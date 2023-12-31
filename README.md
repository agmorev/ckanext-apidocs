# ckanext-apidocs

This extension documents [CKAN APIs](https://docs.ckan.org/en/2.10/api/index.html#api-guide) for developers who want to write code that interacts with CKAN site and its data.
CKAN’s Action API is a powerful, RPC-style API that exposes all of CKAN’s core features to API clients. All of a CKAN website’s core functionality (everything you can do with the web interface and more) can be used by external code that calls the CKAN API.

This plugin provides the option of using the [OpenAPI](https://spec.openapis.org/oas/v3.1.0) and developed on top of the [Swagger UI](https://github.com/swagger-api/swagger-ui).

[Swagger UI](https://github.com/swagger-api/swagger-ui) allows anyone — be it your development team or your end consumers — to visualize and interact with the API’s resources without having any of the implementation logic in place. It’s automatically generated from your OpenAPI (formerly known as Swagger) Specification, with the visual documentation making it easy for back end implementation and client side consumption.


## Requirements

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.9             | not tested    |
| 2.10            | tested        |

Suggested values:

* "yes"
* "not tested" - I can't think of a reason why it wouldn't work
* "not yet" - there is an intention to get it working
* "no"


## Installation

To install ckanext-apidocs:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/agmorev/ckanext-apidocs.git
    cd ckanext-apidocs
    pip install -e .
	pip install -r requirements.txt

3. Add `apidocs` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

3. Add link `apidocs` to the appropriate place on the site, like this:

    ```<a href="{{ h.url_for('apidocs.index') }}">{{ _('CKAN API') }}</a>```

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Config settings

The content of the API actions can be changed or added by making changes to the file `swagger.json` placed in `/public` folder. The file must be created and changed in the same folder `/public` of your project or extension.


## Developer installation

To install ckanext-apidocs for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/agmorev/ckanext-apidocs.git
    cd ckanext-apidocs
    python setup.py develop
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## Releasing a new version of ckanext-apidocs

If ckanext-apidocs should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in the `setup.py` file. See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers) for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:

    pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version:

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI:

       twine upload dist/*

5. Commit any outstanding changes:

       git commit -a
       git push

6. Tag the new release of the project on GitHub with the version number from
   the `setup.py` file. For example if the version number in `setup.py` is
   0.0.1 then do:

       git tag 0.0.1
       git push --tags

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)
