#!/usr/bin/python
from wsgiref.handlers import CGIHandler
import main
import tweet

if not main.app.secret_key:
  import models
  main.app.secret_key = models.config_get('application_secret')
  if not main.app.secret_key:
    import os, base64
    main.app.secret_key = base64.b64encode(os.urandom(24))
    models.config_set('application_secret', main.app.secret_key)

CGIHandler().run(main.app)
