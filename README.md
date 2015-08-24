A self contained (Tornado) REST service for managing running of external Sisyphus commands
such as the quick report generator and quality control suite. Listens on port
10900 for various commands. Try accessing e.g. http://localhost:10900/api/1.0

Manual installation (tested with python > 2.7.6):
    # Install the dependencies and the siswrap package
    pip install -r requirements/dev
    python setup.py install

    # Or do everything in one step
    pip install -e file://`pwd` -r requirements/dev

Manual run
    /usr/local/bin/siswrap-ws --config=./config/siswrap.config --debug

Manual tests
    py.test tests/integration/rest_tests.py

Setup with bells and whistles
    # Use the install script for installation of service and controller scripts.
    # Also runs integration tests in the end
    ./scripts/install

    # Manually control the service afterwards with
    /etc/init.d/siswrap-wsd

    # Manually run integration tests afterwards with
    /usr/local/bin/siswrap-ws-test

Testing within a Docker container
    # This requires access to some of our internal base images
    docker build arteria/siswrap .
    docker run -t -i --name siswrap -p 10900:10900 -v `pwd`:/arteria/arteria-lib/siswrap arteria/siswrap /bin/bash
    # Now you can run the setup and test steps above; and easily re-start everything from scratch
    # by exiting the container and doing
    docker rm siswrap
    # followed by the two earlier docker commands again.
