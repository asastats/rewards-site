Howto
=====

Build documenattion
-------------------

.. code-block:: bash

  cd docs
  make html


Requirements to build latexpdf documentation:

.. code-block:: bash

  sudo apt-get install texlive texlive-latex-extra latexmk


Then build the pdf with:

.. code-block:: bash

  make latexpdf


Setup Redis cache
-----------------

By default, the Rewards Suite uses database as the session engine and caches to memory.
If you want to switch to Redis, replace the existing `SESSION_ENGINE` setting and add `CACHES`:

.. code-block:: python

  # SESSION_ENGINE = "django.contrib.sessions.backends.db"
  SESSION_ENGINE = "django.contrib.sessions.backends.cache"
  CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
  }


There's an existing Ansible role for Redis and you can install it during provisioning
by uncommenting the related line in the `deploy/site_playbook.yml`.


Issue trackers setup
--------------------


GitHub
^^^^^^

GitHub bot
~~~~~~~~~~

Create rewards-bot as a GitHub App and then install it under your organization's settings page.

Assign created app's token to GITHUB_BOT_TOKEN constant in `rewardsweb/.env` file.

GitHub webhook
~~~~~~~~~~~~~~

Go to your repo → Settings → Webhooks → Add webhook

Payload URL: https://rewards.yourdomain.com/webhooks/issue/

Content type: application/json

Secret: Generate and use a strong secret (store it in Django settings)

Events: Select "Issues" or "Let me select individual events" → check "Issues"

Click Add webhook


GitLab
^^^^^^

GitLab Personal Access Token
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To create a Personal Access Token (PAT) in GitLab for use with GitlabProvider, follow these steps:

  1. Log in to your GitLab instance (e.g., gitlab.com or your self-managed instance).

  2. Access your User Settings:

     * Click on your avatar in the top-right corner of the screen.
     * From the dropdown menu, select **Preferences**.

  3. Navigate to Access Tokens:

     * In the left sidebar, click on **Personal access tokens**.

  4. Click Add new token button at the top right:

     * Give your new token a **Name** (e.g., "Gemini CLI Integration" or "Issues Provider").
     * Optionally, set an **Expiration date** for the token. For service accounts, consider a longer but manageable expiration, or rely on rotation
       policies.
     * Select the necessary **Scopes**. For an issues provider, you will likely need:

       * ``api``: Grants complete read/write access to the authenticated user's API, including all groups and projects.
       * ``read_api``: Grants read access to the authenticated user's API, including all groups and projects.
       * ``read_repository`` and ``write_repository`` if your application needs to interact with repository content.

       Choose the minimum scopes required for your application's functionality.

     * Click the **Create personal access token** button.

  5. Save Your Token:

     * **CRITICAL**: Once created, the token will be displayed only once. Copy it immediately and store it securely (e.g., in an environment variable
       ``GITLAB_PRIVATE_TOKEN``) as you will not be able to retrieve it again. If you lose it, you'll have to revoke it and create a new one.


GitLab webhook
~~~~~~~~~~~~~~

Go to Project → Settings → Webhooks

Add URL: https://rewards.yourdomain.com/webhooks/issue/

Add Secret Token (optional but recommended)

Select "Issues events"

Enable SSL verification


Bitbucket
^^^^^^^^^

Bitbucket consumer
~~~~~~~~~~~~~~~~~~

To create a new OAuth consumer (which will give you the "Key" and "Secret" for your BitbucketApp), follow these steps within Bitbucket Cloud:

  1. Log in to Bitbucket Cloud.
  
  2. Navigate to your Workspace:

     * Select your avatar (Your profile picture) from the navigation bar at the top of the screen.
     * Under "Recent workspaces" or "All workspaces", select the specific workspace you want to associate your application with.

  3. Go to Workspace Settings:

     * Once in your workspace, select the Settings cog icon on the top navigation bar.
     * From the dropdown menu, select **Workspace settings**.

  4. Access OAuth Consumers:

     * On the left sidebar, under the "Apps and features" section, select **OAuth consumers**.

  5. Add a New Consumer:

     * Click the **Add consumer** button.
     * Fill in the required information (Name, Description, Callback URL).
     * Click **Save**.
     * After saving, Bitbucket will generate a **Key** (which you'll use as ``BITBUCKET_CLIENT_KEY``) and a **Secret** (which you'll use as ``BITBUCKET_SHARED_SECRET``). You'll need to toggle the consumer name to reveal these values.

Bitbucket webhook
~~~~~~~~~~~~~~~~~

Go to Repository → Repository settings → Webhooks

Add URL: https://rewards.yourdomain.com/webhooks/issue/

Select "Issue: Created, Updated, Deleted"

Add Secret (for Cloud only)


Run Discord bot
---------------

.. code-block:: bash

  PYTHONPATH=rewardsweb python -m rewardsbot.bot


Social media mention trackers
-----------------------------

We have implemented trackers for the following social media platforms:

* X/Twitter

  * official API
  * TwitterAPI.io

* Reddit
* Telegram
* Discord


Run a tracker
^^^^^^^^^^^^^

Use the `run_tracker` management command followed by the tracker's module name:

.. code-block:: bash

  python manage.py run_tracker twitterapiio
