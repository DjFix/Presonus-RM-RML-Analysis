#include "presonus/LinkableComponent.hpp"
#include "presonus/mixer/ChannelComponent.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
struct Boundary : Presonus::linkable_port::Boundary {
  Presonus::LinkableComponent *query(Presonus::LinkableComponent &,
                                     std::uint32_t) override {
    std::abort();
  }
  void remove(Presonus::LinkableComponent &) override { std::abort(); }
  void set(Presonus::LinkableComponent &, Presonus::LinkableComponent &,
           bool) override {
    std::abort();
  }
  void master(Presonus::LinkableComponent &,
              Presonus::LinkableComponent &) override {
    std::abort();
  }
};
struct Dependencies : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action, int, int) override {
    std::abort();
  }
  bool timerLongEnough() const override { std::abort(); }
  bool fadersLocked() const override { std::abort(); }
  const char *activePageName() const override { std::abort(); }
  void paste(void *, const void *, const char *) override { std::abort(); }
};
struct Services : presonus::mixer::ChannelApplicationServices {
  bool isLinked(const Presonus::Mixer::ChannelComponent &) const override {
    std::abort();
  }
  void removeLink(Presonus::Mixer::ChannelComponent &) override {
    std::abort();
  }
  Presonus::Mixer::ChannelComponent *
  linkablePair(Presonus::Mixer::ChannelComponent &) override {
    std::abort();
  }
  void faderLocateDirty(Presonus::Mixer::ChannelComponent &) override {
    std::abort();
  }
  void coefficientsChanged(Presonus::Mixer::ChannelComponent &, bool) override {
    std::abort();
  }
};
int main() {
  Boundary boundary;
  Presonus::linkable_port::State ls;
  Presonus::LinkableComponent link(ls, boundary);
  Core::Portable::Component settings;
  presonus::frontpanel_port::State fs(settings);
  Dependencies deps;
  Presonus::Panel::FrontPanelComponent front(fs, deps);
  presonus::mixer::ChannelState cs;
  Services services;
  Presonus::Mixer::ChannelComponent channel(cs, services);
  presonus::frontpanel_port::ChannelRoute route{channel, link, 0, 0};
  fs.routes = &route;
  fs.routeCount = 1;
  presonus::panel_binding::PanelRegistrarPortState ps;
  Presonus::Panel::PanelRegistrar panel(ps);
  presonus::surface::PanelRegistrarCommandState ss;
  Presonus::Surface::PanelRegistrar surface(ss);
  // Independent adapter contract checks; these are not native fixtures.
  bool rejected = false;
  fs.routeCount = 0;
  try {
    front.getSendPidForAuxChannel(channel);
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  if (!rejected)
    return 3;
  presonus::frontpanel_port::ChannelRoute duplicate[] = {route, route};
  fs.routes = duplicate;
  fs.routeCount = 2;
  rejected = false;
  try {
    front.getSendPidForAuxChannel(channel);
  } catch (const std::invalid_argument &) {
    rejected = true;
  }
  if (!rejected)
    return 4;
  fs.routes = &route;
  fs.routeCount = 1;
  Presonus::Surface::PanelRegistrar unbound;
  rejected = false;
  try {
    unbound.getPort();
  } catch (const std::logic_error &) {
    rejected = true;
  }
  if (!rejected)
    return 5;
  std::string k;
  std::uint64_t a, b, c, d;
  while (std::cin >> k >> a >> b >> c >> d) {
    std::uint32_t result = 0;
    if (k == "slave") {
      ls.slave = a;
      result = link.isLinkSlave();
    } else if (k == "cast")
      result = link.castTo(static_cast<std::int32_t>(a)) != nullptr;
    else if (k == "toggle")
      result = front.isValidToggleBook(static_cast<std::int32_t>(a));
    else if (k == "copy") {
      fs.copyContext = a ? &settings : nullptr;
      result = front.isCopyPasting();
    } else if (k == "map")
      result = panel.mapGroupIdToControlType(
          static_cast<Presonus::Panel::ControlRegistrar::ControlType>(
              static_cast<std::int32_t>(a)));
    else if (k == "name") {
      std::cout << panel.getPanelPortName() << '\n';
      continue;
    } else if (k == "panelport") {
      ps.port = reinterpret_cast<Presonus::IPanelPort *>(
          static_cast<std::uintptr_t>(a));
      result = reinterpret_cast<std::uintptr_t>(panel.getPort());
    } else if (k == "surfaceport") {
      ss.port = reinterpret_cast<Presonus::IPanelPort *>(
          static_cast<std::uintptr_t>(a));
      result = reinterpret_cast<std::uintptr_t>(surface.getPort());
    } else if (k == "send") {
      route.category = a;
      route.index = b;
      ls.partner = c ? &link : nullptr;
      ls.slave = d;
      result = front.getSendPidForAuxChannel(channel);
    } else
      return 2;
    std::cout << result << '\n';
  }
}
