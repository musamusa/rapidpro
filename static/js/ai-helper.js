var homeTab = '/org/home/';
var messagesTab = '/msg/inbox/';
var contactsTab = '/contact/';
var flowsTab = '/flow/';
var analyticsTab = '/ruleset/analytics/';
var campaignsTab = '/campaign/';
var triggersCreateTab = '/trigger/create/';
var triggersTab = '/trigger/';

var urlPath = window.location.pathname;
var analyticsPaths = [homeTab, messagesTab, contactsTab, flowsTab, analyticsTab, campaignsTab, triggersCreateTab, triggersTab];

$(document).ready(function(){
    var isCounting = localStorage.getItem('isCounting');

    if (isCounting === null) {
        try {
            localStorage.setItem('isCounting', 'true');
        } catch(e) {
            console.log(e);
        }
    }

    var countTotal = 0;

    for (var path in analyticsPaths){
        countTotal += getCountClick(analyticsPaths[path]);
    }

    if (isCounting === 'true') {
        if (countTotal >= 10) {
            addAlert('Start here by adding a contact', '.nav-contacts')
        } else {
            if (analyticsPaths.indexOf(urlPath) !== -1){
                addCountClick(urlPath);
            }
        }
    }

    $(".modal .modal-footer .btn-primary").attr('onclick', 'clearCounting();');

});

function clearCounting(){
    for (var path in analyticsPaths){
        localStorage.removeItem(analyticsPaths[path]);
    }
    localStorage.setItem('isCounting', false);
}

function addAlert(msg, tab){
    $(tab).attr('title', msg).attr('data-toggle', 'tooltip');
    $(tab).tooltip('show');
}

function getCountClick(tab){
    var item = localStorage.getItem(tab);
    if (item) {
        return parseInt(item);
    } else {
        return 0;
    }
}

function addCountClick(tab) {
    var count = localStorage.getItem(tab);

    if (!count){
        localStorage.setItem(tab, 1);
    } else {
        count = parseInt(count);
        count++;
        localStorage.setItem(tab, count);
    }
}