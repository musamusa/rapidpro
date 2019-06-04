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

function validateEmbeddedData(form, field_name, value_name) {
    var regex = /[!@#$%^&*()+\-=\[\]{};':"\\|,.<>\/?]/gi;
    var existingFields = [];
    var error = false;
    var embeddedDataFields = form.find('input[name="' + field_name + '"]');
    var embeddedDataValues = form.find('input[name="' + value_name + '"]');
    embeddedDataFields.each(function() {
        var element = $(this);
        var trimValue = $.trim(element.val());
        if (!trimValue.length) {
            element.addClass('invalid');
            element.parent().parent().find('.embed-error-message-field').html('The field is required');
            error = true;
        } else if (regex.test(trimValue)) {
            element.addClass('invalid');
            error = true;
            element.parent().parent().find('.embed-error-message-field').html('Field name can only contain letters, number and underscores');
        } else if (existingFields.indexOf(trimValue) >= 0) {
            element.addClass('invalid');
            error = true;
            element.parent().parent().find('.embed-error-message-field').html('Field names must be unique');
        } else {
            element.removeClass('invalid');
            element.parent().parent().find('.embed-error-message-field').html('');
        }
        existingFields.push(trimValue);
    });
    embeddedDataValues.each(function() {
        var element = $(this);
        var trimValue = $.trim(element.val());
        if (!trimValue.length) {
            element.addClass('invalid');
            element.parent().parent().find('.embed-error-message-value').html('The value is required');
            error = true;
        } else {
            element.removeClass('invalid');
            element.parent().parent().find('.embed-error-message-value').html('');
        }
    });
    return error;
}

function validateEmbeddedDataForTriggerWords(form) {
    var regex = /[!@#$%^&*()+\-=\[\]{};':"\\|,.<>\/?]/gi;
    var existingFields;
    var existingFieldsByName = [];
    var existingValuesByName = [];
    var moreThanOneField = [];
    var moreThanOneValue = [];
    var error = false;
    var embeddedDataFields = form.find('.embed-container').find('.embed-field').find('input');
    var embeddedDataValues = form.find('.embed-container').find('.embed-value').find('input');

    embeddedDataFields.each(function() {
        var fieldName = $(this)[0].name;
        if (existingFieldsByName.indexOf(fieldName) < 0) {
            existingFieldsByName.push(fieldName);
        } else {
            moreThanOneField.push(fieldName);
        }
    });

    embeddedDataValues.each(function() {
        var valueName = $(this)[0].name;
        if (existingValuesByName.indexOf(valueName) < 0) {
            existingValuesByName.push(valueName);
        } else {
            moreThanOneValue.push(valueName)
        }
    });

    for (var item in existingFieldsByName) {
        existingFields = [];
        embeddedDataFields = form.find('input[name="' + existingFieldsByName[item] + '"]');
        embeddedDataFields.each(function() {
            var element = $(this);
            var trimValue = $.trim(element.val());
            if ((!trimValue.length) && (moreThanOneField.indexOf(element[0].name) >= 0)) {
                element.addClass('invalid');
                element.parent().parent().find('.embed-error-message-field').html('The field is required');
                error = true;
            } else if (regex.test(trimValue)) {
                element.addClass('invalid');
                error = true;
                element.parent().parent().find('.embed-error-message-field').html('Field name can only contain letters, number and underscores');
            } else if (existingFields.indexOf(trimValue) >= 0) {
                element.addClass('invalid');
                error = true;
                element.parent().parent().find('.embed-error-message-field').html('Field names must be unique');
            } else {
                element.removeClass('invalid');
                element.parent().parent().find('.embed-error-message-field').html('');
            }
            existingFields.push(trimValue);
        });
    }

    for (item in existingValuesByName) {
        embeddedDataValues = form.find('input[name="' + existingValuesByName[item] + '"]');
        embeddedDataValues.each(function() {
            var element = $(this);
            var trimValue = $.trim(element.val());
            if ((!trimValue.length) && (moreThanOneValue.indexOf(element[0].name) >= 0)) {
                element.addClass('invalid');
                element.parent().parent().find('.embed-error-message-value').html('The value is required');
                error = true;
            } else {
                element.removeClass('invalid');
                element.parent().parent().find('.embed-error-message-value').html('');
            }
        });
    }

    if (error) {
        form.find('.embedded-data-default-message').html('There\'s an error with your submission, please check all ' +
            'fields for each keyword and try again.')
    } else {
        form.find('.embedded-data-default-message').html('');
    }

    return error;
}