function getDomain(hostnameParam) {
    let i,
        h,
        weird_cookie = "registry_get_top_level_domain=cookie",
        hostname = hostnameParam ? hostnameParam.split(".") : document.location.hostname.split(".")
    for (i = hostname.length - 1; i >= 0; i--) {
        h = hostname.slice(i).join(".")
        document.cookie = weird_cookie + ";domain=." + h + ";"
        if (document.cookie.indexOf(weird_cookie) > -1) {
        // We were able to store a cookie! This must be it
        document.cookie =
            weird_cookie.split("=")[0] + "=;domain=." + h + ";expires=Thu, 01 Jan 1970 00:00:01 GMT;"
        return h
        }
    }
}

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function setCookie(name,value,days,domain) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; domain=" + domain + "; path=/";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

var me_current_domain = getDomain(location.hostname);
var meiro_browser = getCookie("meiro_browser");
var meiro_registry = getCookie("meiro_registry");
var terminatingEventSent = false;
var shouldRedirect = false;

function onHide(event) {
    if (!shouldRedirect) return;
    if (event.type == 'pagehide') terminatingEventSent = true;
    if (terminatingEventSent) return;
    if (event.type == 'visibilitychange' && document.visibilityState == 'hidden') {
        window.location.replace("//registry.etstur.com?meiro_browser="+meiro_browser+"&meiro_redirect_uri="+encodeURIComponent(window.location.href));
    }
}

document.addEventListener('visibilitychange', onHide);
window.addEventListener('pagehide', onHide);

if (meiro_browser === null) {
    meiro_browser = uuidv4()
    setCookie("meiro_browser", meiro_browser, 365, me_current_domain);
}

if (meiro_registry === null) {
    var req = new XMLHttpRequest();
    req.overrideMimeType("application/json");
    req.open('GET', "//browser.etstur.com/check?meiro_browser="+meiro_browser, true);
    req.onload  = function() {
        var jsonResponse = JSON.parse(req.responseText);
        if (jsonResponse.hasOwnProperty('meiro_registry') && jsonResponse['meiro_registry'] === true) {
            setCookie("meiro_registry", true, 365, me_current_domain);
        } else {
            shouldRedirect = true;
        }
    };
    req.send(null);
}