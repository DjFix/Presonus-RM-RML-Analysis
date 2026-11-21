#include "presonus/LinkableComponent.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <string_view>

using namespace Core::Portable;
using Presonus::LinkableComponent;
using Presonus::linkable_port::State;
namespace {
struct Boundary final : Presonus::linkable_port::Boundary {
  LinkableComponent *query(LinkableComponent &link, std::uint32_t id) override {
    if (id != 1282304865U)
      std::abort();
    for (std::size_t i = 0; i < links.size(); ++i)
      if (links[i] == &link) {
        std::cout << i << ' ';
        return (i == 6 || (reject && i == 3)) ? nullptr : &link;
      }
    std::abort();
  }
  void remove(LinkableComponent &) override { std::abort(); }
  void set(LinkableComponent &, LinkableComponent &, bool) override {
    std::abort();
  }
  void master(LinkableComponent &, LinkableComponent &) override {
    std::abort();
  }
  std::array<LinkableComponent *, 8> links{};
  bool reject = false;
};

struct ObserveEdit final : ParamObserverBase {
  void paramChanged(Parameter *, int message) override {
    if (message == Parameter::kEdit)
      ++edits;
  }
  int edits = 0;
};

const ParamInfo linked =
    PARAM_INT(11, "linked", -99, 99, 0, nullptr, nullptr, 0, PARAM_LINKABLE);
const ParamInfo missing =
    PARAM_INT(12, "missing", -99, 99, 0, nullptr, nullptr, 0, PARAM_LINKABLE);
const ParamInfo ignored =
    PARAM_INT(13, "ignored", -99, 99, 0, nullptr, nullptr, 0, 0);
} // namespace

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const std::string_view mode(argv[1]);
  const int scenario = std::atoi(argv[2]);
  if (mode == "provider") {
    Boundary boundary;
    State owner, other;
    LinkableComponent left(owner, boundary), right(other, boundary);
    ObserveEdit observer;
    NumericParam source(linked), dest(linked);
    source.setValue(21);
    dest.setValue(-4);
    dest.setController(&observer);
    left.syncParams(source, dest, true);
    owner.alternate.set("token", 90);
    other.alternate.set("old", 17);
    {
      Core::Threads::ScopedLock lock(&State::alternateLock);
      right.copyToAltMemory(owner.alternate);
    }
    std::cout << dest.getIntValue() << ' ' << observer.edits << ' '
              << other.alternate.getInt("token") << ' '
              << (other.alternate.lookup("old") != nullptr) << '\n';
    return 0;
  }
  if (mode != "target")
    return 2;

  Boundary boundary;
  boundary.reject = scenario == 5;
  std::array<ObserveEdit, 8> counters;
  std::array<State, 8> states;
  std::array<std::unique_ptr<LinkableComponent>, 8> link;
  const char *names[] = {"left", "right", "child",  "child",
                         "leaf", "leaf",  "uncast", "unmatched"};
  for (std::size_t i = 0; i < link.size(); ++i) {
    link[i] = std::make_unique<LinkableComponent>(states[i], boundary);
    boundary.links[i] = link[i].get();
    auto &s = states[i];
    s.component.setName(names[i]);
    s.component.addParameters(&linked, 1);
    s.component.addParameters(&ignored, 1);
    if (i % 2 == 0)
      s.component.addParameters(&missing, 1);
    auto *p = s.component.getParameterByTag(11);
    p->setValue(21 + i);
    p->setController(&counters[i]);
    s.component.getParameterByTag(13)->setValue(-20 - static_cast<int>(i));
    s.alternate.set("token", 90 + static_cast<int>(i));
    s.alternate.set(i % 2 == 0 ? "new" : "old", 1);
    s.slave = i % 2 == 0 ? 1 : 0;
    s.enabled = i % 2 == 0 && i < 6;
  }
  states[0].enabled = scenario != 1;
  LinkableComponent *leftChildren[] = {nullptr, link[6].get(), link[7].get(),
                                       link[2].get()};
  LinkableComponent *rightChildren[] = {link[3].get()};
  LinkableComponent *leftNested[] = {link[4].get()};
  LinkableComponent *rightNested[] = {link[5].get()};
  states[0].children = leftChildren;
  states[0].count = 4;
  states[1].children = rightChildren;
  states[1].count = 1;
  states[2].children = leftNested;
  states[2].count = 1;
  states[3].children = rightNested;
  states[3].count = 1;
  if (scenario == 2)
    states[0].partner = link[1].get();
  if (scenario == 3)
    states[1].partner = link[0].get();
  if (scenario == 4)
    states[2].partner = link[3].get();

  link[0]->linkAsMaster(*link[1]);
  std::cout << "|";
  for (std::size_t i = 0; i < 6; ++i) {
    const auto &s = states[i];
    int partner = -1;
    for (std::size_t j = 0; j < link.size(); ++j)
      if (s.partner == link[j].get())
        partner = static_cast<int>(j);
    std::cout << ' ' << partner << ' ' << static_cast<int>(s.slave) << ' '
              << s.component.getParameterByTag(11)->getIntValue() << ' '
              << s.component.getParameterByTag(13)->getIntValue() << ' '
              << counters[i].edits << ' ' << s.alternate.getInt("token") << ' '
              << (s.alternate.lookup("new") != nullptr) << ' '
              << (s.alternate.lookup("old") != nullptr);
  }
  std::cout << '\n';
}
