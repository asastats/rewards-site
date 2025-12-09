Troubleshooting
===============

Ansible output
--------------

Prior to playbook invocation:

.. code-block:: bash

  export ANSIBLE_STDOUT_CALLBACK=debug
  # export ANSIBLE_STDOUT_CALLBACK=yaml


Django errors
-------------

Django logging is configured in settings and it defaults to logging to
the `logs/django-warning.log` file:

.. code-block:: bash

  sudo tail -n 50 /var/www/rewards.asastats.com/logs/django-warning.log


Invalid HTTP_HOST header
^^^^^^^^^^^^^^^^^^^^^^^^

https://stackoverflow.com/a/49817720/11703358

.. code-block:: bash

  if ( $host !~* ^(yourdomain.com|www.yourdomain.com)$ ) {
    return 444;
  }


Linux server errors
-------------------

Check killed processes:

.. code-block:: bash

  sudo dmesg -T | egrep -i 'killed process'+


The following setting will prevent OOM from killing the process:

.. code-block:: ini

  [Service]
  OOMScoreAdjust=-999

