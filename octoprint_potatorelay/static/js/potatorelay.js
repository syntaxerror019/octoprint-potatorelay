$(function () {
    function PotatorelayViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginStateViewModel = parameters[1];

        self.settingsViewModel.potatorelayActiveTab = ko.observable(0);
        self.activeRelays = ko.observableArray([]);

        self.relayLookup = {};

        self.rebuildActiveRelays = function () {
            var settings = self.settingsViewModel.settings.plugins.potatorelay;
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
            OctoPrint.simpleApiCommand("potatorelay", "listAllStatus", {})
                .done(function (response) {
                    (response || []).forEach(function (item) {
                        var entry = self.relayLookup[item.id];
                        if (entry) {
                            entry.status(!!item.status);
                        }
                    });
                })
                .fail(function () {
                    console.log("potatorelay: failed to fetch relay statuses");
                });
        };

        self.toggleRelay = function (relay) {
            if (relay.status() && relay.confirm_off) {
                if (!window.confirm("Turn OFF '" + relay.label + "'?")) {
                    return;
                }
            }
            OctoPrint.simpleApiCommand("potatorelay", "update", {subject: relay.id})
                .done(function (response) {
                    relay.status(!!response.status);
                });
        };

        self.onUserLoggedIn = self.onStartupComplete = function () {
            self.rebuildActiveRelays();
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "potatorelay") {
                return;
            }
            if (data.type === "status" && self.relayLookup[data.id]) {
                self.relayLookup[data.id].status(!!data.status);
            }
        };

        self.onSettingsShown = self.onSettingsHidden = function () {
            self.settingsViewModel.potatorelayActiveTab(0);
        };

        self.onSettingsBeforeSave = function () {
            self.rebuildActiveRelays();
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: PotatorelayViewModel,
        dependencies: ["settingsViewModel", "loginStateViewModel"],
        elements: ["#navbar_plugin_potatorelay"]
    });
});
