from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseNotFound, HttpResponseRedirect

from forms import MomentumSignupForm


## MOMENTUM SPECIFIC CODE BELOW

def momentum_signup(request):
    if request.method == 'POST':
        form = MomentumSignupForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect("/dashboard")
    else:
        form = MomentumSignupForm(
            initial={
                "name": request.GET.get("name", ""),
                "email": request.GET.get("email", ""),
                "area": request.GET.get("area", ""),
            }
        )

    return render_to_response("signup-momentum.html", locals(), context_instance=RequestContext(request))


def dashboard(request):
    return render_to_response("dashboard-momentum.html", locals(), context_instance=RequestContext(request))