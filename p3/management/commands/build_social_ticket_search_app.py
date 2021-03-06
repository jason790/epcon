# -*- coding: utf-8 -*-
"""
    Build Social Ticket Search App
    ------------------------------

    Creates a single-page fuzzy full text search list with all tickets
    and their social ticket IDs.  Writes the single page to
    ep-social-ticket-search-app/index.html

    This can be used during registration to do quick search in the
    list of all tickets in order to find badges or find that no badge
    exists.

    Usage:
    
    cd epcon
    ./manage.py build_social_ticket_search_app ep2017
    cd ep-social-ticket-search-app
    ./run.sh
    
    This will build the search app and start a web server running
    on port 8000. Pointing a browser at http://localhost:8000/ will
    then load the app into the browser.

    Author: Marc-Andre Lemburg, 2016-2017.

"""
import sys

from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from conference import models as cmodels
from conference import utils
from p3 import models

from collections import defaultdict
from optparse import make_option
import operator

### Globals

TEMPLATE = u"""\
<!DOCTYPE html>
<html>
<title>EuroPython %(year)s Social Ticket Search App</title>
<meta name="viewport" content="width=device-width, initial-scale=0.9">
<link rel="stylesheet" href="css/materialize.min.css">
<head>
<meta charset=utf-8 />
<title>EuroPython %(year)s Social Ticket Search App</title>
</head>
<body>

<h3 class="center-align hide-on-small-only">EuroPython %(year)s Social Ticket Search App</h3>

<div id="ticket-list" class="container">

<p>
<label for="exact_search" class="hide-on-small-only">Exact search</label>
<input id="exact_search" type="text" class="search" placeholder="Exact search"/>
<label for="fuzzy_search" class="hide-on-small-only">Fuzzy search</label>
<input id="fuzzy_search" type="text" class="fuzzy-search" placeholder="Fuzzy search"/>
</p>

<p class="row">
<button class="sort btn col s5" data-sort="name">Sort by name</button>
<button class="sort btn col s5 offset-s2" data-sort="tid">Sort by ticket ID</button>
</p>

%(listing)s

</div>

<script src="js/jquery.min.js"></script>
<script src="js/jquery.map.min.js"></script>
<script src="js/list.js"></script>
<script src="js/list.fuzzysearch.js"></script>
<script src="js/materialize.min.js"></script>
<script>
var fuzzyOptions = {
  searchClass: "fuzzy-search",
  location: 0,
  distance: 100,
  threshold: 0.1,
  multiSearch: true
};
var ticketList = new List('ticket-list', { 
  valueNames: ['name', 'email', 'tid'], 
  plugins: [ListFuzzySearch(fuzzyOptions)]
});
</script>
</body>
</html>
"""

### Helpers

def profile_url(user):

    return urlresolvers.reverse('conference-profile',
                                args=[user.attendeeprofile.slug])

def attendee_name(ticket, profile=None):

    # Determine user name from profile, if available
    if profile is not None:
        name = u'%s %s' % (
            profile.user.first_name,
            profile.user.last_name)
    else:
        name = ''

    # Remove whitespace
    name = name.strip()

    # Use ticket name if not set in profile
    if not name:
        name = ticket.name.strip()
        
    # Convert to title case, if not an email address
    if u'@' not in name:
        name = name.title()

    return name

def attendee_list_key(entry):

    # Sort by name
    return entry[1][2]

def create_app_file(conference, output_file):

    output = open(output_file, 'wb')

    # Get all valid conference tickets (frozen ones are not valid)
    tickets = cmodels.Ticket.objects.filter(
        fare__conference=conference,
        fare__ticket_type='event',
        orderitem__order___complete=True,
        frozen=False,
        )

    # Find all attendees
    attendee_dict = {}
    missing_profiles = []
    for ticket in tickets:
        #sys.stderr.write('ticket %r: conference=%s\n' %
        #                 (ticket, ticket.fare.conference))
        profile = None
        email = ticket.user.email
        name = attendee_name(ticket, profile)
        attendee_dict[ticket.id] = (
            ticket,
            profile,
            name,
            email)

    # Prepare list
    attendee_list = attendee_dict.items()
    attendee_list.sort(key=attendee_list_key)

    # Print list of attendees
    l = [u'<table class="striped">',
         u'<thead>',
         u'<tr>'
         u'<th data-field="name">Name</th>',
         u'<th data-field="email" class="hide-on-small-only">Email</th>',
         u'<th data-field="tid">TID</th>',
         u'<th data-field="tcode" class="hide-on-small-only">Code</th>',
         u'</tr>'
         u'</thead>',
         u'<tbody class="list">',
         ]
    for id, (ticket, profile, name, email) in attendee_list:
        l.append((u'<tr>'
                  u'<td class="name">%s</td>'
                  u'<td class="email hide-on-small-only">%s</td>'
                  u'<td class="tid">%s</td>'
                  u'<td class="tcode hide-on-small-only">%s</td>'
                  u'</tr>' %
                  (name,
                   email,
                   id,
                   ticket.fare.code)))
    l.extend([u'</tbody>',
              u'</table>',
              u'<p>%i attendees in total.</p>' % len(attendee_list),
              ])
    output.write((TEMPLATE % {
                      'listing': u'\n'.join(l),
                      'year': conference[2:],
                  }).encode('utf-8'))

###

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        # make_option('--output',
        #      action='store',
        #      dest='talk_status',
        #      default='accepted',
        #      choices=['accepted', 'proposed'],
        #      help='The status of the talks to be put in the report. '
        #           'Choices: accepted, proposed',
        # ),
    )

    args = '<conference> [<output-file>]'

    def handle(self, *args, **options):
        
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')
        try:
            output_file = args[1]
        except IndexError:
            output_file = 'ep-social-ticket-search-app/index.html'

        create_app_file(conference, output_file)
