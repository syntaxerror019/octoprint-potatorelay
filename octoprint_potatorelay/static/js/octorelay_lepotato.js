$(function () {
    function OctorelayLepotatoViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginStateViewModel = parameters[1];

        self.octorelayActiveTab = ko.observable(0);
        self.activeRelays = ko.observableArray([]);

        self.relayLookup = {};

        self.rebuildActiveRelays = function () {
            var settings = self.settingsViewModel.settings.plugins.octorelay_lepotato;
            if (!settings) {
                return;
            }
            var relays = settings.relays();
            var active = [];
            self.relayLookup = {};

            relays.forEach(function (relay, index) {
                if (!relay.active()) {
                    return;
                }
                var id = "r" + (index + 1);
                var entry = {
                    id: id,
                    label: relay.label(),
                    icon_on: relay.icon_on(),
                    icon_off: relay.icon_off(),
                    confirm_off: relay.confirm_off(),
                    status: ko.observable(false)
                };
                self.relayLookup[id] = entry;
                active.push(entry);
            });

            self.activeRelays(active);
            self.refreshAllStatus();
        };

        self.refreshAllStatus = function () {
            OctoPrint.simpleApiCommand("octorelay_lepotato", "listAllStatus", {})
                .done(function (response) {
                    (response || []).forEach(function (item) {
                        var entry = self.relayLookup[item.id];
                        if (entry) {
                            entry.status(!!item.status);
                        }
                    });
                })
                .fail(function () {
                    console.log("octorelay_lepotato: failed to fetch relay statuses");
                });
        };

        self.toggleRelay = function (relay) {
            if (relay.status() && relay.confirm_off) {
                if (!window.confirm("Turn OFF '" + relay.label + "'?")) {
                    return;
                }
            }
            OctoPrint.simpleApiCommand("octorelay_lepotato", "update", {subject: relay.id})
                .done(function (response) {
                    relay.status(!!response.status);
                });
        };

        self.onUserLoggedIn = self.onStartupComplete = function () {
            self.rebuildActiveRelays();
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "octorelay_lepotato") {
                return;
            }
            if (data.type === "status" && self.relayLookup[data.id]) {
                self.relayLookup[data.id].status(!!data.status);
            }
        };

        self.onSettingsShown = self.onSettingsHidden = function () {
            self.octorelayActiveTab(0);
        };

        self.onSettingsBeforeSave = function () {
            self.rebuildActiveRelays();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: OctorelayLepotatoViewModel,
        dependencies: ["settingsViewModel", "loginStateViewModel"],
        elements: ["#navbar_plugin_octorelay_lepotato", "#settings_plugin_octorelay_lepotato"]
    });
});
