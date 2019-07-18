window.simulation = false
moving_sim = false
level_classes = {"I": "iinfo", "W": "iwarn", "E": "ierror"}
response_timeout = null

window.updateSimulator = (data) ->
  ussd = if window.ussd then "ussd" else ""

  $(".simulator-body").html ""
  i = 0

  $('.simulator-body').data('message-count', data.messages.length)

  if data.ruleset
    $('.simulator-footer .media-button').hide()

    if data.ruleset.ruleset_type == 'wait_gps'
      $('.simulator-footer .imessage').hide()
      $('.simulator-footer .gps-button').show()
    else if data.ruleset.ruleset_type == 'wait_photo'
      $('.simulator-footer .imessage').hide()
      $('.simulator-footer .photo-button').show()
    else if data.ruleset.ruleset_type == 'wait_video'
      $('.simulator-footer .imessage').hide()
      $('.simulator-footer .video-button').show()
    else if data.ruleset.ruleset_type == 'wait_audio'
      $('.simulator-footer .imessage').hide()
      $('.simulator-footer .audio-button').show()
    else if data.ruleset.ruleset_type == 'all_that_apply'
      $('.simulator-footer .imessage').hide()
      $('.simulator-footer .options-button').show()
    else
      $('.simulator-footer .imessage').show()

      for rule in data.ruleset.rules
        if rule.test.type == 'timeout'
          response_timeout = setTimeout(nextFlowStepFromTimeout, rule.test.minutes * 1000)

  else
    $('.simulator-footer .media-button').hide()
    $('.simulator-footer .imessage').show()


  while i < data.messages.length
    msg = data.messages[i]

    model = (if (msg.model is "msg") then "imsg" else "ilog")
    level = (if msg.level? then level_classes[msg.level] else "")
    direction = (if (msg.direction is "O") then "from" else "to")

    media_type = null
    media_viewer_elt = null

    quick_replies = null
    apply_options = null

    metadata = msg.metadata
    if metadata and metadata.quick_replies?
      quick_replies = "<div id='quick-reply-content'>"
      for reply in metadata.quick_replies
        quick_replies += "<button class=\"btn quick-reply\" data-payload=\"" + reply + "\"> " + reply + "</button>"
      quick_replies += "</div>"

    if metadata and metadata.apply_options?
      apply_options = "<div class='apply-options-content' data-msg='" + msg.id + "'>"

      if metadata.apply_options.options?
        apply_options += "<div id='options-" + msg.id + "' data-options='" + metadata.apply_options.options.join() + "'></div>"
        for option in metadata.apply_options.options

          apply_options += "<div class='item-option'>"

          apply_options += "<label class='apply-option'>" + option + "</label>"

          apply_options += "<label class='option-label true' data-msg='" + msg.id + "' data-field='" + msg.id + "-" + option + "-true' data-value='true'>"
          apply_options += metadata.apply_options.option_true + "<input class='option-hidden' type='radio' name='" + msg.id + "-" + option + "' value='" + metadata.apply_options.option_true + "' data-value='true'/>"
          apply_options += "</label>"

          apply_options += "<label class='option-label false' data-msg='" + msg.id + "' data-field='" + msg.id + "-" + option + "-false' data-value='false'>"
          apply_options += metadata.apply_options.option_false + "<input class='option-hidden' type='radio' name='" + msg.id + "-" + option + "' value='" + metadata.apply_options.option_false + "' data-value='false'/>"
          apply_options += "</label>"

          apply_options += "</div>"

      apply_options += "</div>"

    if msg.attachments and msg.attachments.length > 0
      attachment = msg.attachments[0]
      parts = attachment.split(':')
      media_type = parts[0]
      media_url = parts.slice(1).join(":")

      if media_type == 'geo'
        media_type = 'icon-pin_drop'
      else
        media_type = media_type.split('/')[0]
        if media_type == 'image'
          media_type = 'icon-photo_camera'
          media_viewer_elt = "<span class=\"media-file\"><img src=\"" + media_url + "\"></span>"
        else if media_type == 'video'
          media_type = 'icon-videocam'
          media_viewer_elt = "<span class=\"media-file\"><video controls src=\"" + media_url + "\"></span>"
        else if media_type == 'audio'
          media_type = 'icon-mic'
          media_viewer_elt = "<span class=\"media-file\"><audio controls src=\"" + media_url + "\"></span>"

    ele = "<div class=\"" + model + " " + level + " " + direction + " " + ussd
    if media_type
      ele += " media-msg"
    ele += "\">"
    ele += msg.text
    ele += "</div>"

    if quick_replies
      ele_quick_replies = "<div class='ilog " + level + " " + direction + " " + ussd + "'>"
      ele_quick_replies += quick_replies
      ele_quick_replies += "</div>"
      ele += ele_quick_replies

    if apply_options
      ele_apply_options = "<div class='ilog " + level + " " + direction + " " + ussd + "'>"
      ele_apply_options += apply_options
      ele_apply_options += "</div>"
      ele += ele_apply_options

    if msg.text or quick_replies or apply_options
      $(".simulator-body").append(ele)
    if media_type and media_viewer_elt
      $(".simulator-body").append(media_viewer_elt)
    i++
  $(".simulator-body").scrollTop $(".simulator-body")[0].scrollHeight
  $("#simulator textarea").val ""

  $(".btn.quick-reply").on "click", (event) ->
    payload = event.target.innerText
    sendMessage(payload)

  $("label.option-label").on "click", (event) ->
    field = event.currentTarget.dataset.field
    value = event.currentTarget.dataset.value
    if value == 'true'
      other_field = field.replace('-true', '-false')
    else
      other_field = field.replace('-false', '-true')
    $('label[data-field="' + other_field + '"]').removeClass 'checked'
    $('label[data-field="' + field + '"]').addClass 'checked'

  if window.simulation

    # this is for angular to show activity
    scope = $('body').scope()
    if scope
      scope.$apply ->
        scope.visibleActivity =
          active: data.activity
          visited: data.visited

    for node in $('#workspace').children('.node')
      node = $(node).data('object')
      node.setActivity(data)

  activity = $('.activity:visible,.node .active:visible')
  if activity
    if activity.offset()
      top = activity.offset().top
      $('html, body').animate
        scrollTop : top - 200

$ ->
  $(window).scroll (evt) ->
    fitSimToScreen()

# Textarea expansion
# [eric] not entirely sure what sort of magic is happening here
toExpand = $("#simulator textarea")
initTextareaHeight = toExpand.height()
initSimulatorBody = $(".simulator-body").height()
resized = toExpand.height()
toExpand.autosize callback: ->
  currentResized = toExpand.height()
  unless currentResized is resized
    footer = currentResized + 10
    resized = currentResized
    $(".simulator-footer").css "height", footer
    $(".simulator-body").css "height", initSimulatorBody - footer + 30
    $(".simulator-body").scrollTop $(".simulator-body")[0].scrollHeight


# check form errors
checkForm = (newMessage) ->
  valid = true
  if newMessage is ""
    $("#simulator textarea").addClass "error"
    valid = false
  else if newMessage.length > 160
    $("#simulator textarea").val ""
    $("#simulator textarea").addClass "error"
    valid = false
  toExpand.css "height", initTextareaHeight
  $(".simulator-footer").css "height", initTextareaHeight + 10
  $(".simulator-body").css "height", "360px"
  return valid

processForm = (postData) ->
    # if we are currently saving to don't post message yet
    scope = $('html').scope('scope')
    if scope and scope.saving
      setTimeout ->
        processForm(postData)
      , 500
      return

    $.post(getSimulateURL(), JSON.stringify(postData)).done (data) ->

      # reset our form input
      $('.simulator-footer .media-button').hide()
      $('.simulator-footer .imessage').show()
      window.updateSimulator(data)

      # hide loading first
      $(".simulator-loading").css "display", "none"
      $(".simulator-body").css "height", "360px"

    $("#simulator textarea").removeClass "error"

sendMessage = (newMessage) ->
  if checkForm(newMessage)
    if response_timeout
      clearTimeout(response_timeout)
    processForm({new_message: newMessage})

sendPhoto = ->
  processForm({new_photo: true})

sendVideo = ->
  processForm({new_video: true})

sendAudio = ->
  processForm({new_audio: true})

sendGPS = ->
  processForm({new_gps: true})

fitSimToScreen = ->
  top = $(window).scrollTop()
  sim = $("#simulator")
  workspace = $("#workspace")
  showSim = $("#show-simulator")

  if top > 110 and not sim.hasClass('scrollfix')
    sim.addClass('scrollfix')
    showSim.addClass('scrollfix')
  else if top <= 110 and sim.hasClass('scrollfix')
    sim.removeClass('scrollfix')
    showSim.removeClass('scrollfix')

  simTop = sim.offset().top
  simBottom = sim.height() + simTop
  workspaceBottom = workspace.offset().top + workspace.height()

  if simTop > top + 10 and sim.hasClass('on-footer')
    sim.removeClass('on-footer')
  else
    if simBottom > workspaceBottom - 30 and not sim.hasClass('on-footer')
      sim.addClass('on-footer')

    if simBottom < workspaceBottom and sim.hasClass('on-footer')
      sim.removeClass('on-footer')

hideSimulator = ->
  moving_sim = true
  sim = $("#simulator")
  sim.animate right: - (sim.outerWidth() + 10), 400, "easeOutExpo", ->
    sim.hide()
    showButton = $("#show-simulator")
    showButton.css({ right:  - (showButton.outerWidth() + 10)})
    showButton.show()
    showButton.stop().animate { right:0, width: 40 }, 400, "easeOutExpo"
    moving_sim = false

  window.simulation = false
  $("#toolbar .actions").fadeIn();

  # this is the hook into angular
  # show our normal activity when the sim is hidden
  scope = $('body').scope()
  if scope
    scope.$apply ->
      scope.visibleActivity = scope.activity

  if window.is_voice
    window.hangup()

getSimulateURL = ->
  scope = $('html').scope()
  if scope and scope.language
    return window.simulateURL + '?lang=' + scope.language.iso_code
  return window.simulateURL

showSimulator = (reset=false) ->

  messageCount = $(".simulator-body").data('message-count')

  if reset or not messageCount or messageCount == 0
    resetSimulator()
  else
    refreshSimulator()

  moving_sim = true
  fitSimToScreen()
  $("#toolbar .actions").fadeOut();
  $("#show-simulator").stop().animate { right: '-110px' }, 200, ->
    $(this).hide()
    $(this).find('.message').hide()
    sim = $("#simulator")
    sim.css({ right:  - (sim.outerWidth() + 10)})
    sim.show()
    sim.animate right: 30, 400, "easeOutExpo", ->
      $(".simulator-content textarea").focus()
      moving_sim = false
  window.simulation = true

window.nextFlowStepFromTimeout = ->
  clearTimeout(response_timeout)
  sendMessage('MSG_TIMEOUT')

window.refreshSimulator = ->

  # if we are currently saving to don't post message yet
  scope = $('html').scope('scope')
  if scope and scope.saving
    setTimeout(refreshSimulator, 500)
    return

  $.post(getSimulateURL(), JSON.stringify({ has_refresh:false })).done (data) ->
    window.updateSimulator(data)
    if window.ivr and window.simulation
      setTimeout(window.refreshSimulator, 2000)

window.resetSimulator = ->
  $(".simulator-body").html ""
  $(".simulator-body").append "<div class='ilog from'>One moment..</div>"

  # reset our form input
  $('.simulator-footer .media-button').hide()
  $('.simulator-footer .imessage').hide()

  # if we are currently saving to don't post message yet
  scope = $('html').scope('scope')
  if scope and scope.saving
    setTimeout(resetSimulator, 500)
    return

  $.post(getSimulateURL(), JSON.stringify({ has_refresh:true })).done (data) ->
    window.updateSimulator(data)
    if window.ivr and window.simulation
      setTimeout(window.refreshSimulator, 2000)

window.hangup = ->
  $(".simulator-body").html ""
  $.post(getSimulateURL(), JSON.stringify({ hangup:true })).done (data) ->

appendMessage = (newMessage, ussd=false) ->
  ussd = if ussd then "ussd " else ""
  imsgDiv = '<div class=\"imsg ' + ussd + 'to post-message\"></div>'
  $(imsgDiv).text(newMessage).appendTo(".simulator-body")
  $("#simulator textarea").val ""
  $(".simulator-loading").css "display", "block"
  # $(".simulator-body").css "height", $(".simulator-body").height() - 25
  $(".simulator-body").scrollTop $(".simulator-body")[0].scrollHeight

#-------------------------------------
# Event bindings
#-------------------------------------

$('#simulator .gps-button').on 'click', ->
  sendGPS();

$('#simulator .photo-button').on 'click', ->
  sendPhoto()

$('#simulator .simulator-footer .imessage .send-photo').on 'click', ->
  sendPhoto()

$('#simulator .video-button').on 'click', ->
  sendVideo()

$('#simulator .audio-button').on 'click', ->
  sendAudio()

$('#simulator .options-button').on 'click', (event) ->
  content_tag = $('.apply-options-content').last()
  msg_id = content_tag[0].dataset.msg
  options_tag = $('#options-' + msg_id).last()
  options = options_tag[0].dataset.options
  arrayOptions = options.split(",")

  txtMessage = ''
  for option, i in arrayOptions
    tagInput = $("input[name='" + msg_id + "-" + option + "']:checked")

    if tagInput.length == 0
      alert('Please, select all that apply options before sending.')
      break
    else
      if tagInput[0].dataset.value == 'true'
        txtMessage += option
        txtMessage += if (i + 1) == arrayOptions.length then '' else ','
      else
        txtMessage += if (i + 1) == arrayOptions.length then '' else ','

    if (i + 1) == arrayOptions.length
      sendMessage(txtMessage)

# send new message to simulate
$("#simulator .send-message").on "click", ->
  newMessage = $("#simulator textarea").val()
  $(this).addClass("to-ignore")
  sendMessage(newMessage)

  # add the progress gif
  if window.ussd and newMessage.length <= 182
    appendMessage newMessage, true
  else if newMessage.length <= 160 and newMessage.length > 0
    appendMessage newMessage

# send new message on key press (enter)
$("#simulator textarea").keypress (event) ->
  if event.which is 13
    event.preventDefault()
    newMessage = $("#simulator textarea").val()
    sendMessage(newMessage)

    # add the progress gif
    if newMessage
      if window.ussd and newMessage.length <= 182
        appendMessage newMessage, true
      else if newMessage.length <= 160
        appendMessage newMessage

$("#show-simulator").hover ->
  if not moving_sim
    $(this).stop().animate {width: '110px'}, 200, "easeOutBack", ->
      $(this).find('.message').stop().fadeIn('fast')
, ->
  if not moving_sim
    $(this).find('.message').hide()
    $(this).stop().animate { width: '40px'}, 200, "easeOutBack", ->

verifyNumberSimulator = ->
  if window.ivr
    modal = new Modax(gettext("Start Test Call"), '/usersettings/phone/')
    modal.setIcon("icon-phone")
    modal.setListeners
      onSuccess: ->
        showSimulator(true)
    modal.show()

  else if window.ussd and not window.has_ussd_channel
    modal = new Modal(gettext("Missing USSD Channel"), gettext("There is no channel that supports USSD connected. Please connect a USSD channel first."))
    modal.setIcon("icon-phone")
    modal.setListeners
      onPrimary: ->
        modal.dismiss()
    modal.show()
  else
    showSimulator()

$("#show-simulator").click ->
  verifyNumberSimulator()

# toggle simulator
$("#toggle-simulator").on "click", ->
  if not $("#simulator").is(":visible")
    verifyNumberSimulator()
  else
    hideSimulator()

# close the simulator
$(".simulator-close").on "click", ->
  hideSimulator()

# refresh the simulator
$(".simulator-refresh").on "click", ->
  window.resetSimulator()

