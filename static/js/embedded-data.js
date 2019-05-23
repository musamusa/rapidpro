function addEmbed(field, value, is_on_keyword_trigger, trigger_flow_keyword) {
    var template;
    try {
        var value_parsed = $.parseHTML(value);
        value = value_parsed[0].data;
    } catch (e) {
        if (value) {
            console.warn('Error during parseHTML command for the value "' + value + '" on embedded data');
            value = null
        }
    }
    if (is_on_keyword_trigger) {
        template = $('.embed-template-keyword').clone();
        template.find('.embed-field-keyword').find('input').attr('name', 'embedded_field_keyword').attr('value', field);
        template.find('.embed-value-keyword').find('input').attr('name', 'embedded_value_keyword').attr('value', value);
        if (field) {
            template.find('.embed-field-slug').html('@embed.' + field);
        }
        template.toggleClass('embed-template-keyword');
        template.addClass('embed-counter-keyword');
        $('.embed-container-keyword').append(template);
        $('.embed-header-keyword').removeClass('inactive');
    } else if (trigger_flow_keyword) {
        template = $('.embed-template-' + trigger_flow_keyword).clone();
        template.find('.embed-field-' + trigger_flow_keyword).find('input').attr('name', 'embedded_field_' + trigger_flow_keyword).attr('value', field);
        template.find('.embed-value-' + trigger_flow_keyword).find('input').attr('name', 'embedded_value_' + trigger_flow_keyword).attr('value', value);
        if (field) {
            template.find('.embed-field-slug-' + trigger_flow_keyword).html('@embed.' + field);
        }
        template.toggleClass('embed-template');
        template.toggleClass('embed-template-' + trigger_flow_keyword);
        template.addClass('embed-counter-' + trigger_flow_keyword);
        $('.embed-container-' + trigger_flow_keyword).append(template);
        $('.embed-header-' + trigger_flow_keyword).removeClass('inactive');
    } else {
        template = $('.embed-template').clone();
        template.find('.embed-field').find('input').attr('name', 'embedded_field').attr('value', field);
        template.find('.embed-value').find('input').attr('name', 'embedded_value').attr('value', value);
        if (field) {
            template.find('.embed-field-slug').html('@embed.' + field);
        }
        template.toggleClass('embed-template');
        template.addClass('embed-counter');
        $('.embed-container').append(template);
        $('.embed-header').removeClass('inactive');
    }
}

function removeEmbed(el, is_on_keyword_trigger, trigger_flow_keyword) {
    el.parent().remove();
    var length_embed;
    if (is_on_keyword_trigger) {
        length_embed = $('.embed-counter-keyword');
        if (length_embed.length == 0) {
            $('.embed-header-keyword').addClass('inactive');
        }
    } else if (trigger_flow_keyword) {
        length_embed = $('.embed-counter-' + trigger_flow_keyword);
        if (length_embed.length == 0) {
            addEmbed("", "", "", trigger_flow_keyword);
        }
    } else {
        length_embed = $('.embed-counter');
        if (length_embed.length == 0) {
            $('.embed-header').addClass('inactive');
        }
    }
}
