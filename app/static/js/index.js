

function tinyxhr(url, cb, method, post, contentType)
{
  var requestTimeout,xhr;
  try {
    xhr = new XMLHttpRequest();
  }
  catch(e)
  {
    try {
      xhr = new ActiveXObject("Msxml2.XMLHTTP");
    }
    catch (e)
    {
      if(console)
      {
        console.log("tinyxhr: XMLHttpRequest not supported");
      }
      return null;
    }
  }

  requestTimeout = setTimeout(function(){
    xhr.abort();
    cb(new Error("tinyxhr: aborted by a timeout"), "",xhr);
  }, 10000);

  xhr.onreadystatechange = function()
  {
    if (xhr.readyState != 4)
      return;
    clearTimeout(requestTimeout);
    cb(xhr.status != 200 ?
      new Error("tinyxhr: server response status is " + xhr.status)
      : false, xhr.responseText, xhr);
  }

  method = method || "GET"
  xhr.open(method.toUpperCase(), url, true);

  if(!post)
    xhr.send();
  else
  {
    xhr.setRequestHeader('Content-type', contentType || 'application/x-www-form-urlencoded');
    xhr.send(post);
  }
}

(function()
{

  document.getElementById('toggle').addEventListener('click', function (e)
  {
    document.getElementById('tuckedMenu').classList.toggle('custom-menu-tucked');
    document.getElementById('toggle').classList.toggle('x');
  });

  var frame_updates = {};

  function update_frames(init)
  {
    frames = [
      'workers',
      'lbry_setup'
    ];

    frames.forEach(function(f)
    {
      var now = +(new Date());
      if(init)
      {
        frame_updates[f] = now;
      }

      if(now - frame_updates[f] < 5000)
      {
        return;
      }

      frame_updates[f] = now;
      var url = "/" + f;
      var callback = function(err, data, xhr)
      {
        frame_updates[f] = +(new Date);
        if(err)
        {
          console.error(err);
          return;
        }

        document.getElementById(f).outerHTML = data;
      };

      tinyxhr(url, callback, "get", false, "text/html");
    });
  };

  window.startPoll = function()
  {
    if(window.updateInterval)
        return;

    update_frames(true)
    window.updateInterval = setInterval(update_frames, 1000);
  }

  window.stopPoll = function()
  {
    clearInterval(window.updateInterval);
    window.updateInterval = undefined;
  }

  window.execCmd = function(uri)
  {
    var callback = function(err, data, xhr)
    {
      if(err)
        return toast(err);

      try
      {
        data = JSON.parse(data);
      }
      catch(e)
      {
        console.warn("not json: %s", data);
      }

      if(data instanceof Object)
      {
        if ("error" in data)
        {
          data = new Error(data.error);
        }
        else if("message" in data)
        {
          data = data.message;
        }
      }

      toast(data);
    };

    toast("calling: " + uri);
    tinyxhr(uri, callback, "get", false, "text/html");
  };

  var toast = function(data)
  {
    var err = false;
    if(data instanceof Error)
    {
        err = true;
        data = data.message;
    }

    var t = document.getElementById('toast');
    var tt = document.getElementById('toast_text');

    tt.innerHTML = data;
    var classes = ['toast'];
    if(err)
        classes.push('toast-err');

    t.className = classes.join(' ');
  };

  // TODO remove
  window.toast = toast;

  var toastClose = function()
  {
    var t = document.getElementById('toast').className = 'toast hidden';
  };


  document.getElementById('toast_close').addEventListener('click', toastClose);
  window.startPoll();

  window.nav = function(uri)
  {
    location.href = uri;
  };

})();




Page = {
    prev: function(slug, page)
    {
        return Page.turn(slug, page - 1);
    },
    next: function(slug, page)
    {
        return Page.turn(slug, page + 1);
    },
    turn: function(slug, page)
    {
        var uri = ([slug, page, this.Sort.field, this.Sort.dir]).join("/");
        var callback = function(err, data)
        {
            if(!err)
            {
                document.getElementById(slug).outerHTML = data;
            }
        }
        tinyxhr(uri, callback, "get", false, "text/html");
    },
    sort: function(slug, field)
    {
        console.log("sort: %s", field);
        this.Sort.set(field);
        this.turn(slug, 1);
    },
    Sort: {
        field: 'id',
        dir: 'asc',
        ASC: 'asc',
        DESC: 'desc',
        set: function(f){
            if(this.field == f)
            {
                this.flipDir();
            }

            this.field = f;
        },
        flipDir: function()
        {
            if(this.dir == this.ASC)
            {
                this.dir = this.DESC;
            }
            else
            {
                this.dir = this.ASC;
            }
        }
    }
};