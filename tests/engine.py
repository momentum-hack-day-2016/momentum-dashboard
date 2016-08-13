from hitchserve import ServiceBundle
#from os import path, system, chdir
import hitchserve
import hitchpostgres
import hitchselenium
import hitchpython
import hitchredis
import hitchsmtp
import hitchtest


# Get directory above this file
#PROJECT_DIRECTORY = path.abspath(path.join(path.dirname(__file__), '..'))

class ExecutionEngine(hitchtest.ExecutionEngine):
    """Python engine for running tests."""

    def set_up(self):
        """Set up your applications and the test environment."""
        self.path.project = self.path.engine.joinpath("..")

        self.python_package = hitchpython.PythonPackage(
            python_version=self.settings['python_version']
        )
        self.python_package.build()


        self.python_package.cmd.pip("install", "-r", "requirements/local.txt").in_dir(self.path.project).run()
        
        self.manage = self.python_package.cmd.python("-u", "manage.py")\
                                             .in_dir(self.path.project)\
                                             .with_trailing_args("--settings", "config.settings.local")\
                                             .with_env(
                                                DATABASE_URL="postgres://dashboard:password@127.0.0.1:15432/dashboard",
                                                SECRET_KEY="cj5^uos4tfCdfghjkf5hq$9$(@-79^e9&x$3vyf#igvsfm4d=+",
                                                CELERY_BROKER_URL="redis://localhost:16379",
                                                DJANGO_EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
                                             )
        
        postgres_package = hitchpostgres.PostgresPackage(
            version=self.settings["postgres_version"],
        )
        postgres_package.build()

        redis_package = hitchredis.RedisPackage(
            version=self.settings.get("redis_version")
        )
        redis_package.build()

        firefox_package = hitchselenium.FirefoxPackage()
        firefox_package.build()

        self.services = ServiceBundle(
            project_directory=self.path.project,
            startup_timeout=float(self.settings["startup_timeout"]),
            shutdown_timeout=float(self.settings["shutdown_timeout"]),
        )

        # Docs : https://hitchtest.readthedocs.org/en/latest/plugins/hitchpostgres.html

        # Postgres user and database
        postgres_user = hitchpostgres.PostgresUser("dashboard", "password")

        self.services['Postgres'] = hitchpostgres.PostgresService(
            postgres_package=postgres_package,
            users=[postgres_user, ],
            port=15432,
            databases=[hitchpostgres.PostgresDatabase("dashboard", postgres_user), ]
        )


        self.services['Django'] = hitchserve.Service(
            command=self.manage("runserver", "8000", "--noreload"),
            log_line_ready_checker=lambda line: "Quit the server with CONTROL-C" in line,
            needs=[self.services['Postgres'],],
        )

        # Docs : https://hitchtest.readthedocs.org/en/latest/plugins/hitchsmtp.html
        self.services['HitchSMTP'] = hitchsmtp.HitchSMTPService(port=10025)

        # Docs : https://hitchtest.readthedocs.org/en/latest/plugins/hitchredis.html
        self.services['Redis'] = hitchredis.RedisService(
            redis_package=redis_package,
            port=16379,
        )

        # Docs : https://hitchtest.readthedocs.org/en/latest/plugins/hitchselenium.html

        self.services['Firefox'] = hitchselenium.SeleniumService(
            firefox_binary=firefox_package.firefox,
            xvfb=self.settings.get("xvfb", False) or self.settings.get("quiet", False),
            no_libfaketime=True,
        )

        self.services.startup(interactive=False)

        self.manage("migrate", "--noinput").run()

        # Docs : https://hitchtest.readthedocs.org/en/latest/plugins/hitchselenium.html
        self.driver = self.services['Firefox'].driver

        self.webapp = hitchselenium.SeleniumStepLibrary(
            selenium_webdriver=self.driver,
            wait_for_timeout=5,
        )

        self.click = self.webapp.click
        self.wait_to_appear = self.webapp.wait_to_appear
        self.wait_to_contain = self.webapp.wait_to_contain
        self.wait_for_any_to_contain = self.webapp.wait_for_any_to_contain
        self.click_and_dont_wait_for_page_load = self.webapp.click_and_dont_wait_for_page_load

        # Configure selenium driver
        screen_res = self.settings.get(
            "screen_resolution", {"width": 1024, "height": 768, }
        )
        self.driver.set_window_size(
            int(screen_res['width']), int(screen_res['height'])
        )
        self.driver.set_window_position(0, 0)
        self.driver.implicitly_wait(2.0)
        self.driver.accept_next_alert = True

    def load_website(self, url):
        self.driver.get("http://localhost:8000/{}".format(url))

    def fill_form(self, **kwargs):
        for item, value in kwargs.items():
            self.driver.find_element_by_id(item).send_keys(value)

    def pause(self, message=None):
        """Pause test and launch IPython"""
        if hasattr(self, 'services'):
            self.services.start_interactive_mode()
        self.ipython(message)
        if hasattr(self, 'services'):
            self.services.stop_interactive_mode()

    def wait_for_email(self, containing=None):
        """Wait for email."""
        self.services['HitchSMTP'].logs.out.tail.until_json(
            lambda email: containing in email['payload'] or containing in email['subject'],
            timeout=45,
            lines_back=1,
        )

    def confirm_emails_sent(self, number):
        """Count number of emails sent by app."""
        assert len(self.services['HitchSMTP'].logs.json()) == int(number)

    def time_travel(self, days=""):
        """Get in the Delorean, Marty!"""
        self.services.time_travel(days=int(days))

    def connect_to_kernel(self, service_name):
        """Connect to IPython kernel embedded in service_name."""
        self.services.connect_to_ipykernel(service_name)

    def on_failure(self):
        """Runs if there is a test failure"""
        if not self.settings['quiet']:
            if self.settings.get("pause_on_failure", False):
                self.pause(message=self.stacktrace.to_template())

    def on_success(self):
        """Runs when a test successfully passes"""
        if self.settings.get("pause_on_success", False):
            self.pause(message="SUCCESS")

    def tear_down(self):
        """Run at the end of all tests."""
        if hasattr(self, 'services'):
            self.services.shutdown()
