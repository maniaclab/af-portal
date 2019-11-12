jQuery(document).ready(function() {
  "use strict";

  var pluginName = "Morphext",
  defaults = {
    animation: "bounceIn",
    separator: ",",
    speed: 2000,
    complete: jQuery.noop
  };

  function Plugin (element, options) {
    this.element = jQuery(element);
    this.settings = jQuery.extend({}, defaults, options);
    this._defaults = defaults;
    this._init();
  }

  Plugin.prototype = {
    _init: function () {
      var jQuerythat = this;
      this.phrases = [];

      this.element.addClass("morphext");

      jQuery.each(this.element.text().split(this.settings.separator), function (key, value) {
        jQuerythat.phrases.push(jQuery.trim(value));
      });

      this.index = -1;
      this.animate();
      this.start();
    },
    animate: function () {
      this.index = ++this.index % this.phrases.length;
      this.element[0].innerHTML = "<span class=\"animated " + this.settings.animation + "\">" + this.phrases[this.index] + "</span>";

      if (jQuery.isFunction(this.settings.complete)) {
        this.settings.complete.call(this);
      }
    },
    start: function () {
      var jQuerythat = this;
      this._interval = setInterval(function () {
        jQuerythat.animate();
      }, this.settings.speed);
    },
    stop: function () {
      this._interval = clearInterval(this._interval);
    }
  };

    jQuery.fn[pluginName] = function (options) {
      return this.each(function() {
        if (!jQuery.data(this, "plugin_" + pluginName)) {
          jQuery.data(this, "plugin_" + pluginName, new Plugin(this, options));
        }
      });
    };

  // Hero rotating texts
  jQuery("#hero .rotating").Morphext({
    animation: "flipInX",
    separator: "/",
    speed: 3000
  });
});
