// Closes responsive menu when a scroll trigger link is clicked
jQuery('.js-scroll-trigger').click(function() {
  jQuery('.navbar-collapse').collapse('hide');
});

// Activate scrollspy to add active class to navbar items on scroll
jQuery('body').scrollspy({
  target: '#mainNav',
  offset: 54
});


// Back to top button
$(document).ready(function(){
    $(window).scroll(function(){
        if ($(this).scrollTop() > 100) {
            $('#scroll').fadeIn();
        } else {
            $('#scroll').fadeOut();
        }
    });
    $('#scroll').click(function(){
        $("html, body").animate({ scrollTop: 0 }, 600);
        return false;
    });
});

$(document).ready(function () {

    $('#sidebarCollapse').on('click', function () {
        $('#sidebar').toggleClass('active');
    });
});
