function addEmbed() {
    var template = $('.embed-template').clone();
    template.find('.embed-field').find('input').attr('name', 'embedded_field');
    template.find('.embed-value').find('input').attr('name', 'embedded_value');
    template.toggleClass('embed-template');
    template.addClass('embed-counter');
    $('.embed-container').append(template);
    $('.embed-header').removeClass('inactive');
}

function removeEmbed(el) {
    el.parent().remove();
    var length_embed = $('.embed-counter');
    if (length_embed.length == 0) {
        $('.embed-header').addClass('inactive');
    }
}

$(document).ready(function() {});