$(function () {
    function PotatorelayViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];
        self.loginStateViewModel = parameters[1];

        self.activeTab = ko.observable(0);
        self.activeRelays = ko.observableArray([]);
        self.relayLookup = {};
        self._settingsBound = false;

        self.rebuildActiveRelays = function () {
            var pluginSettings = self.settingsViewModel.settings &&
                self.settingsViewModel.settings.plugins &&
                self.settingsViewModel.settings.plugins.potatorelay;
            if (!pluginSettings) {
                return;
            }
            var relays = pluginSettings.relays();
            if (!relays) return;
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

        self.onAfterBinding = function () {
            self.rebuildActiveRelays();
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

        self.onSettingsShown = function () {
            self.activeTab(0);
            if (!self._settingsBound) {
                var el = document.getElementById("settings_plugin_potatorelay");
                if (el) {
                    ko.applyBindings(self, el);
                    self._settingsBound = true;
                }
            }
        };

        self.onSettingsHidden = function () {
            self.activeTab(0);
            self.rebuildActiveRelays();
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
