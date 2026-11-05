#include "presonus/mixer/MixerComponentBase.hpp"
#include "presonus/panel/FrontPanelComponent.hpp"
#include "presonus/panel/PanelRegistrar.hpp"
#include "presonus/panel/RackPanelComponent.hpp"
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <new>
namespace {
void *allocated[2048]{};
int live = 0, attempts = 0, failure = -1;
bool track = false;
void remember(void *p) {
  if (track) {
    assert(live < 2048);
    allocated[live++] = p;
  }
}
void forget(void *p) {
  for (int i = 0; i < live; ++i)
    if (allocated[i] == p) {
      allocated[i] = allocated[--live];
      return;
    }
}
struct DefaultPanel : Presonus::Panel::PanelComponent {
  DefaultPanel() = default;
};
struct FrontDependencies : presonus::frontpanel_port::Dependencies {
  void perform(presonus::frontpanel_port::Action, int, int) override {}
  bool timerLongEnough() const override { return false; }
  bool fadersLocked() const override { return false; }
  const char *activePageName() const override { return nullptr; }
  void paste(void *, const void *, const char *) override {}
};
struct RackDependencies : presonus::rackpanel_port::Dependencies {
  Core::Portable::Component component;
  std::vector<presonus::rackpanel_port::Channel> list;
  Presonus::Panel::ControlGroup &group(int) override {
    throw std::logic_error("not used");
  }
  Core::Portable::Component &monitorParameters() override { return component; }
  const std::vector<presonus::rackpanel_port::Channel> &
  channels() const override {
    return list;
  }
  int numClients() const override { return 0; }
  void removeDelegate(Presonus::Panel::RackPanelComponent &) override {}
};
void timer(const Presonus::DelayTimer &t) {
  auto s = presonus::timing::DelayTimerAccess::get(t);
  assert(!s.start && s.duration == 1000 && !s.elapsed &&
         s.reciprocal == 1.f / 1000.f && !s.executing);
}
} // namespace
void *operator new(std::size_t n) {
  if (track && attempts++ == failure)
    throw std::bad_alloc();
  void *p = std::malloc(n ? n : 1);
  if (!p)
    throw std::bad_alloc();
  remember(p);
  return p;
}
void *operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void *p) noexcept {
  forget(p);
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
void operator delete[](void *p) noexcept { ::operator delete(p); }
void operator delete[](void *p, std::size_t) noexcept { ::operator delete(p); }
int main() {
  Presonus::Mixer::MixerComponentBase mixer;
  presonus::panel_binding::PanelRegistrarPortState ps;
  Presonus::Panel::PanelRegistrar registrar(ps);
  {
    DefaultPanel p;
    auto &s = p.portableState();
    assert(s.ownedComponent.get() == &s.component &&
           s.component.feedbackNeeded());
    timer(s.encoderTimer);
    timer(s.buttonTimer);
    assert(!s.mixer && !s.registrar);
  }
  {
    Presonus::Panel::FrontPanelComponent f(mixer, registrar);
    auto &s = f.portableState();
    auto &state = f.portableFrontState();
    assert(s.ownedComponent.get() == &s.component &&
           s.component.feedbackNeeded());
    assert(s.mixer == &mixer && s.registrar == &registrar);
    timer(s.encoderTimer);
    timer(s.buttonTimer);
    assert(&state.settings == &s.component &&
           state.panelParameters == &s.component);
    assert(s.component.countParameters() == 136);
    for (int i = 0; i < 136; ++i) {
      auto *p = s.component.getParameterAt(i);
      assert(p && p == s.component.getParameterByTag(p->getTag()));
      assert(p->getValue() == p->getDefault());
    }
    assert(s.component.getParameterByTag(300) &&
           s.component.getParameterByTag(301));
  }
  {
    Core::Portable::Component settings;
    presonus::frontpanel_port::State state(settings);
    FrontDependencies d;
    Presonus::Panel::FrontPanelComponent f(state, d);
    assert(&f.portableFrontState() == &state && &state.settings == &settings);
    assert(f.portableState().ownedComponent.get() ==
           &f.portableState().component);
    RackDependencies rd;
    Presonus::Panel::RackPanelComponent r(rd);
    assert(r.countParameters() == 0);
    assert(!r.portableState().ownedComponent);
    r.monitorSource(123, false);
    r.cleanup();
  }
  {
    Presonus::Panel::RackPanelComponent r(mixer, registrar);
    assert(&r.portableState().component ==
           static_cast<presonus::panel_port::PanelCore *>(&r));
    assert(!r.portableState().ownedComponent);
    assert(r.countParameters() == 5);
    bool failed = false;
    try {
      r.monitorSource(4, true);
    } catch (const std::logic_error &) {
      failed = true;
    }
    assert(failed);
  }
  // Warm provider singleton allocations before measuring scoped failures.
  {
    Presonus::Panel::FrontPanelComponent f(mixer, registrar);
  }
  int failures = 0, successes = 0;
  for (int which = 0; which < 3; ++which) {
    int successfulAllocations = 0;
    track = true;
    failure = -1;
    attempts = 0;
    if (which == 0) {
      DefaultPanel p;
    } else if (which == 1) {
      Presonus::Panel::RackPanelComponent p(mixer, registrar);
    } else {
      Presonus::Panel::FrontPanelComponent p(mixer, registrar);
    }
    successfulAllocations = attempts;
    track = false;
    assert(live == 0);
    for (int stop = 0; stop < successfulAllocations; ++stop) {
      failure = stop;
      attempts = 0;
      track = true;
      bool threw = false;
      try {
        if (which == 0) {
          DefaultPanel p;
        } else if (which == 1) {
          Presonus::Panel::RackPanelComponent p(mixer, registrar);
        } else {
          Presonus::Panel::FrontPanelComponent p(mixer, registrar);
        }
      } catch (const std::bad_alloc &) {
        threw = true;
      }
      track = false;
      assert(threw);
      if (live)
        std::cerr << "leak which=" << which << " fail=" << stop
                  << " remaining=" << live << "\n";
      assert(live == 0);
      ++failures;
    }
    ++successes;
  }
  std::cout << "PASS owner identity, FrontPanel136, borrowed adapters, two "
               "base timers; allocation failures "
            << failures << " success paths " << successes << '\n';
}
