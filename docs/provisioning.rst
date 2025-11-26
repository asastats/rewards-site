Provisioning
============

``Ansible`` is Python package used to deploy rewards-suite infrastructure.

This guide is made for ``Ubuntu Server 24.04.03 LTS`` hosts, but it's applicable for many other Debian based Linux/GNU distros.


Local machine requirements
--------------------------

Ansible installation
^^^^^^^^^^^^^^^^^^^^

The most recent stable Ansible version is available through ``pip`` and its Python 3 version for Debian systems is called python3-pip.

.. code-block:: bash

  sudo apt-get install python3-pip

.. code-block:: bash

  pip3 install ansible --user


Server requirements/setup
-------------------------

Production
^^^^^^^^^^

SSH access
""""""""""

For majority of VPS providers, **root** user is already configured and ssh access is allowed by provided public key.


Virtual machine
^^^^^^^^^^^^^^^

Local network setup
"""""""""""""""""""

Configuration for Ubuntu 24.04.3 server:

.. code-block:: bash
  :caption: /etc/netplan/50-cloud-init.yaml

  network:
    version: 2
    ethernets:
      enp0s3:
        dhcp4: false
        addresses:
          - 192.168.1.82/24
        routes:
          - to: default
            via: 192.168.1.1
        nameservers:
          addresses: [8.8.8.8, 4.4.4.4]


Configuration from above is activated by `sudo netplan apply`.


SSH access
""""""""""

Server should have ``openssh-server`` installed and running. Many GNU/Linux have Python 3 preinstalled.

.. code-block:: bash

  sudo apt-get install openssh-server python3


For testing purposes in VM environment, a temporary user should be created. Upon first start it will enable the root login by running:

.. code-block:: bash

    tempuser@ubuntu:~# sudo passwd root


In Ubuntu ssh login for root is restricted, so it should be temporary allowed:

.. code-block:: bash

  sudo nano /etc/ssh/sshd_config
  PermitRootLogin yes


Default identity public key copying (use -i identity_file for different identity) from the local machine is issued by:

.. code-block:: bash

    ssh-copy-id root@192.168.1.82


Temporary user should be deleted afterwards:

.. code-block:: bash

    ssh root@192.168.1.82 "userdel tempuser; rm -rf /home/tempuser"


Project provisioning
--------------------

.. warning::

  Before using in production, you need to update the content of the error pages in the ``rewardsweb/templates/`` directory,
  as well as the ``static/auth_privacy.html`` and ``static/auth_terms.html`` HTML pages to reflect your company name.

Use the following commands to deploy the Rewards Suite on your testing server:

.. code-block:: bash

  # testing (virtual machine)
  ansible-playbook -i hosts --limit=testing site_playbook.yml


Similarly, for your production server use:

.. code-block:: bash

  # production
  ansible-playbook -i hosts --limit=production site_playbook.yml


For debugging purpose, add `-vv` or `-vvvv` for more verbose output:

.. code-block:: bash

  ansible-playbook -vv -i hosts --limit=testing site_playbook.yml


Upgrade system and project
^^^^^^^^^^^^^^^^^^^^^^^^^^

Issue the following command if you want to fully upgrade system and Python packages to the latest versions:

.. code-block:: bash

  ansible-playbook -i hosts --limit=production --tags=upgrade site_playbook.yml


Update project code
^^^^^^^^^^^^^^^^^^^

After code has changed, issue the following command to apply those changes:

.. code-block:: bash

  ansible-playbook -i hosts --limit=production --tags=update-project-code site_playbook.yml
