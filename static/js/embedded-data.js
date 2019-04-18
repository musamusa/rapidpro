function addEmbed(field, value, is_on_keyword_trigger) {
    var template;
    if (is_on_keyword_trigger) {
        template = $('.embed-template-keyword').clone();
        template.find('.embed-field-keyword').find('input').attr('name', 'embedded_field_keyword').attr('value', field);
        template.find('.embed-value-keyword').find('input').attr('name', 'embedded_value_keyword').attr('value', value);
        template.toggleClass('embed-template-keyword');
        template.addClass('embed-counter-keyword');
        $('.embed-container-keyword').append(template);
        $('.embed-header-keyword').removeClass('inactive');
    } else {
        template = $('.embed-template').clone();
        template.find('.embed-field').find('input').attr('name', 'embedded_field').attr('value', field);
        template.find('.embed-value').find('input').attr('name', 'embedded_value').attr('value', value);
        template.toggleClass('embed-template');
        template.addClass('embed-counter');
        $('.embed-container').append(template);
        $('.embed-header').removeClass('inactive');
    }
}

function removeEmbed(el, is_on_keyword_trigger) {
    el.parent().remove();
    var length_embed;
    if (is_on_keyword_trigger) {
        length_embed = $('.embed-counter-keyword');
        if (length_embed.length == 0) {
            $('.embed-header-keyword').addClass('inactive');
        }
    } else {
        length_embed = $('.embed-counter');
        if (length_embed.length == 0) {
            $('.embed-header').addClass('inactive');
        }
    }
}