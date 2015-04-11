import flask
import re
import sh

app = flask.Flask(__name__)
app.config.from_pyfile('instance/default.cfg')
app.config.from_envvar('CONFIG_FILE', silent=True)

def get_and_validate_host(request):
    """Confirms that request's host parameter is a host or ip(v6)

    returns None on failure.
    """
    target = request.args.get('host')
    if target is None:
        return
    match = re.search("^[a-zA-Z0-9\-\.:]+$", target)
    if match is not None:
        return target
    return

def execute(encoder, command, *args, **kwargs):
    """Runs <command> with *args and **kwargs, then handles output using the
    requested <encoder>.

    For raw output, a generator is used to stream results.
    """
    def raw_stream_generator():
        """Generator for streaming output"""
        try:
            for chunk in command(*args, _iter=True, **kwargs):
                yield flask.escape(chunk)
        except sh.ErrorReturnCode:
            pass
    if encoder == "raw":
        return flask.Response(raw_stream_generator(), mimetype='text/html')
    elif encoder == "json":
        try:
            output = command(*args, **kwargs)
            status = 0
        except sh.ErrorReturnCode as exc:
            output = exc.stdout
            status = exc.exit_code
        return flask.jsonify({
            "output": "{0}".format(output),
            "status": status
        })
    else:
        return flask.escape("Error, invalid encoder")

def error_response(encoder, error):
    """Responds with <error> text based on <encoder>"""
    if encoder == "json":
        return flask.jsonify({
            "output": error,
            "status": 1
        })
    else:
        return flask.escape(error)

@app.route("/<encoder>/host")
def api_host(encoder):
    target = get_and_validate_host(flask.request)
    if target is None:
        return error_response(encoder, "Error, invalid host")
    return execute(
        encoder,
        sh.host,
        target
    )

@app.route("/<encoder>/mtr<version>")
def api_mtr(encoder, version):
    target = get_and_validate_host(flask.request)
    if target is None:
        return error_response(encoder, "Error, invalid host")
    if version not in ('4', '6'):
        return error_response(encoder, "Error, invalid ip version")
    return execute(
        encoder,
        sh.mtr,
        '-{0}'.format(version),
        '--report',
        '--report-wide',
        target,
        c=4
    )

@app.route("/<encoder>/ping<version>")
def api_ping(encoder, version):
    target = get_and_validate_host(flask.request)
    if target is None:
        return error_response(encoder, "Error, invalid host")
    if version == '4':
        command = sh.ping
    elif version == '6':
        command = sh.ping6
    else:
        return error_response(encoder, "Error, invalid ip version")
    return execute(
        encoder,
        command,
        target,
        c=4,
        i=1,
        w=8
    )

@app.route("/<encoder>/traceroute<version>")
def api_traceroute(encoder, version):
    target = get_and_validate_host(flask.request)
    if target is None:
        return error_response(encoder, "Error, invalid host")
    if version not in ('4', '6'):
        return error_response(encoder, "Error, invalid ip version")
    return execute(
        encoder,
        sh.traceroute,
        '-{0}'.format(version),
        target,
        A=True,
        w=2
    )
    
@app.route("/")
def index():
    return flask.render_template(
        'index.html',
        site_name = app.config["SITE_NAME"],
        theme = app.config["THEME"],
        site_location = app.config["SITE_LOCATION"],
        test_ipv4 = app.config["TEST_IPV4"],
        test_ipv6 = app.config["TEST_IPV6"],
        test_files = app.config["TEST_FILES"],
        additional_lgs = app.config["ADDITIONAL_LG_LIST"],
        
        peering_asn = app.config["PEERING_ASN"],
        peering_map_url = app.config["PEERING_MAP_URL"],
	    peering_contact = app.config["PEERING_CONTACT"],
        peering_policy = app.config["PEERING_POLICY"]
    )

if __name__ == "__main__":
    app.run()
