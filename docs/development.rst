Development
===========

Setup
-----

The requirements necessary to use this project on a development machine are:

.. code-block:: bash

  sudo apt-get install git python3 python3-venv postgresql postgresql-contrib


Python environment
^^^^^^^^^^^^^^^^^^

Create Python virtual environment:

.. code-block:: bash

  python3 -m venv rewards


Set some environment variables upon activation:

.. code-block:: bash
  :caption: /home/username/dev/venvs/rewards/bin/activate

  export DJANGO_SETTINGS_MODULE=rewardsweb.settings.development


Activate Python environment:

.. code-block:: bash

  source rewards/bin/activate


Adding an alias can be useful:

.. code-block:: bash
  :caption: ~/.bashrc

  alias 'rwds'='cd /home/username/dev/rewards-suite/rewardsweb;source /home/username/dev/venvs/rewards/bin/activate'


Initial packages installation:

.. code-block:: bash

  (rewards) debian:~/dev/rewards-suite/rewardsweb$ pip install -r requirements/development.txt
  (rewards) debian:~/dev/rewards-suite/rewardsweb$ pip install -r requirements/contract.txt


Run development server
----------------------

.. code-block:: bash

  python manage.py runserver


PostgreSQL
----------

PostgreSQL setup in development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Database creation on development machine:

.. code-block:: bash

  root@debian:~# su - postgres
  postgres@debian:~# createdb rewards_db


Database user setup on development machine (CREATEDB is needed for running tests, while
pg_trgm extension is used for determining the similarity of text based on trigram matching):

.. code-block:: bash

  postgres@debian:~# psql
  postgres=# CREATE USER rewards_user WITH ENCRYPTED PASSWORD 'mypassword';
  postgres=# ALTER USER rewards_user CREATEDB;
  postgres=# ALTER DATABASE rewards_db OWNER TO rewards_user;
  postgres=# \connect rewards_db
  postgres=# CREATE EXTENSION IF NOT EXISTS pg_trgm;


Finally, under rewards web Python environemnt:

.. code-block:: bash

  python manage.py makemigrations
  python manage.py migrate


DaisyUI
-------

Follow the instructions found
`here <https://daisyui.com/docs/install/django/>`. One of the alternatives to **watchman**
is **entr** (you can install it on Debain based systems with `sudo apt-get install entr`),
invoke the following trigger build/watch command to use it:

.. code-block:: bash

  $ ls core/static/css/*.css | entr core/static/css/tailwindcss \
    -i core/static/css/input.css -o core/static/css/style.css \
    --config core/static/css/tailwind.config.js --minify


Smart contract
--------------

Compile
^^^^^^^

After you activated the Python environment, you can compile smart contract by issuing the following commands:

.. code-block:: bash

  cd rewardsweb
  algokit compile py contract/contract.py --out-dir artifacts


Deploy, fund, and setup dApp
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a shortcat Django management command that will deploy generated smart contract on the blockchain,
fund the related account with required ALGO, and finally set up the dApp with rewards token ID and
claim period duration values retrieved from the environemnt variables:

.. code-block:: bash

  python manage.py deploy_dapp testnet


Tests
-----

Python
^^^^^^

Run all unit tests:

.. code-block:: bash

  cd /home/username/dev/rewards-suite/rewardsweb
  source /home/username/dev/venvs/rewards/bin/activate
  python -m pytest -v  # or just pytest -v


Run tests matching pattern:

.. code-block:: bash

  pytest -v -k test_contributor_model  # pytest -vvv for more verbose output


Run project's functional tests:

.. code-block:: bash

  python -m pytest functional_tests/ -v


Run all smart contract tests:

.. code-block:: bash

  python -m pytest contract/tests/ -v --cov=contract --cov-branch
