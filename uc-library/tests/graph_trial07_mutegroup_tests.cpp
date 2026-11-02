#include "presonus/StormMuteGroupComponent.hpp"
#include <array>
#include <cstring>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace Core::Portable;
using namespace presonus::storm_mute_port;
namespace {
std::vector<std::string> trace;
template <class... T> void event(const char *name, T... values) {
  std::ostringstream s;
  s << "[\"" << name << "\"";
  ((s << ',' << values), ...);
  s << ']';
  trace.push_back(s.str());
}
struct Param : NumericParam {
  int id;
  float v;
  Param(const ParamInfo &i, int id, float v) : NumericParam(i), id(id), v(v) {}
  float getValue() const override { return v; }
  void setValue(float value, bool edit) override {
    v = value;
    event("set", id, value, int(edit));
  }
};
struct TestTimer : TimerFixture {
  int id;
  bool running = false, longEnough = false;
  explicit TestTimer(int id) : id(id) {}
  bool executing() const override {
    event("executing", id);
    return running;
  }
  bool elapsed() const override {
    event("elapsed", id);
    return longEnough;
  }
  void end() override { event("end", id); }
  void reset() override { event("reset", id); }
};
struct Client : Component {
  Component *remote = nullptr;
  Component *findChild(const char *) const override {
    event("remoteLookup");
    return remote;
  }
};
struct Boundaries : Services, Observer {
  State *state = nullptr;
  Client *client = nullptr;
  bool connected = false, loadOK = false;
  void refreshSip() override { event("refreshSip"); }
  void activate(unsigned int i) override {
    event("activate", i, int(state->recalling));
  }
  Component *connectedClient() override {
    event("connected");
    return connected ? client : nullptr;
  }
  void muteGroupStored(int i) override { event("muteGroupStored", i); }
  bool load(Group &g) override {
    int i = state->groups.index(&g);
    event("load", i);
    return loadOK;
  }
  void allDirty(Presonus::StormMuteGroupComponent &, bool dirty) override {
    event("allDirty", int(dirty));
  }
  void groupDirty(Presonus::StormMuteGroupComponent &, unsigned int i,
                  bool dirty) override {
    event("groupDirty", i, int(dirty));
  }
};
std::vector<int> readList() {
  int count;
  std::cin >> count;
  std::vector<int> v(count);
  for (auto &x : v)
    std::cin >> x;
  return v;
}
template <class V> void list(std::ostream &s, const V &v) {
  s << '[';
  bool first = true;
  for (auto &x : v) {
    if (!first)
      s << ',';
    first = false;
    s << x;
  }
  s << ']';
}
} // namespace
int providerSmoke() {
  Timer missing;
  int rejected = 0;
  try {
    missing.executing();
  } catch (const std::logic_error &) {
    ++rejected;
  }
  try {
    missing.elapsed();
  } catch (const std::logic_error &) {
    ++rejected;
  }
  try {
    missing.end();
  } catch (const std::logic_error &) {
    ++rejected;
  }
  try {
    missing.reset();
  } catch (const std::logic_error &) {
    ++rejected;
  }
  if (missing.present() || rejected != 4)
    return 9;

  Presonus::DelayTimer real(1.f);
  presonus::timing::DelayTimerAccess::set(real, {0, 10, 20, 0.1f, false});
  Timer timer{&real, nullptr};
  if (timer.executing() || !timer.elapsed())
    return 10;
  timer.reset();
  if (timer.executing() || timer.elapsed())
    return 11;
  // Exercise real provider lookup/observer notifications using actual
  // NumericParam.
  Boundaries boundary;
  State state(boundary);
  boundary.state = &state;
  Component remote;
  Client client;
  client.remote = &remote;
  boundary.client = &client;
  boundary.connected = true;
  const ParamInfo info[] = {
      PARAM_FLOAT(19, "status", 0, 1, 0, 1, nullptr, nullptr, 0, 0)};
  remote.addParameters(info, 1);
  presonus::mute_group_port::State groupState;
  Group group(groupState);
  state.groups.add(&group);
  state.observer = &boundary;
  Presonus::StormMuteGroupComponent component(state);
  component.onCascadeStateChange(true);
  auto *p = remote.getParameterByTag(19);
  if (!p || groupState.alternateStatus != p)
    return 12;
  trace.clear();
  p->setValue(1.f, false);
  if (trace != std::vector<std::string>{"[\"groupDirty\",0,0]"})
    return 13;
  component.onCascadeStateChange(false);
  trace.clear();
  p->setValue(0.f, false);
  if (!trace.empty() || groupState.alternateStatus)
    return 14;
  std::cout << "real CCL observer add/remove/notification and DelayTimer "
               "provider bindings passed\n";
  return 0;
}
int main(int argc, char **argv) {
  if (argc == 2 && std::string(argv[1]) == "--provider-smoke")
    return providerSmoke();
  int method;
  while (std::cin >> method) {
    std::uint32_t index;
    int flag, param, tag, msg, enabled, recalling, busy, stored, oldRemote,
        allGroup, observer, connected, remoteComponent, loadOK, messageMatch;
    std::string name;
    std::cin >> index >> flag >> param >> name >> tag >> msg >> enabled >>
        recalling >> busy >> stored >> oldRemote >> allGroup >> observer >>
        connected >> remoteComponent >> loadOK >> messageMatch;
    std::array<float, 84> values;
    for (auto &v : values)
      std::cin >> v;
    const auto loose = readList(), delayed = readList(), localTags = readList(),
               remoteTags = readList(), timerPresent = readList(),
               executing = readList(), elapsed = readList();
    std::array<ParamInfo, 84> infos{};
    std::vector<std::unique_ptr<Param>> params;
    for (int i = 0; i < 84; ++i) {
      infos[i].type = ParamInfo::kFloat;
      infos[i].tag = i == param ? tag : i;
      std::strncpy(infos[i].name, i == param ? name.c_str() : "p", 31);
      params.emplace_back(new Param(infos[i], i, values[i]));
    }
    Boundaries boundary;
    State state(boundary);
    boundary.state = &state;
    boundary.connected = connected;
    boundary.loadOK = loadOK;
    std::array<presonus::mute_group_port::State, 3> groupStates;
    Group g0(groupStates[0]), g1(groupStates[1]), g2(groupStates[2]);
    g0.file = true;
    g0.busy = busy;
    g0.stored = stored;
    g2.all = true;
    state.groups.add(&g0);
    state.groups.add(&g1);
    state.groups.add(&g2);
    const std::array<std::vector<int>, 3> initial = {
        std::vector<int>{0, 1}, std::vector<int>{1, 2}, std::vector<int>{3}};
    for (int i = 0; i < 3; ++i) {
      for (int p : initial[i])
        groupStates[i].members.add(params[p].get());
      if (oldRemote)
        groupStates[i].alternateStatus = params[9 + i].get();
    }
    for (int p : loose)
      state.loose.add(params[p].get());
    for (int p : delayed)
      state.delayed.add(params[p].get());
    for (int p : {0, -1, 2, 3})
      state.mixerMutes.add(p < 0 ? nullptr : params[p].get());
    state.enabled = enabled;
    state.recalling = recalling;
    state.allGroup = allGroup ? &g2 : nullptr;
    state.observer = observer ? &boundary : nullptr;
    std::array<TestTimer, 4> timers = {TestTimer(0), TestTimer(1), TestTimer(2),
                                       TestTimer(3)};
    for (int i = 0; i < 4; ++i) {
      timers[i].running = executing[i];
      timers[i].longEnough = elapsed[i];
    }
    for (int i = 0; i < 3; ++i)
      state.storeTimers.add(
          Timer{nullptr, timerPresent[i] ? &timers[i] : nullptr});
    state.releaseTimer.fixture = &timers[3];
    Component remote;
    Client client;
    client.remote = remoteComponent ? &remote : nullptr;
    boundary.client = &client;
    std::vector<ParamInfo> localInfos(localTags.size()),
        remoteInfos(remoteTags.size());
    for (unsigned i = 0; i < localInfos.size(); ++i) {
      localInfos[i].type = ParamInfo::kFloat;
      localInfos[i].tag = localTags[i];
    }
    for (unsigned i = 0; i < remoteInfos.size(); ++i) {
      remoteInfos[i].type = ParamInfo::kFloat;
      remoteInfos[i].tag = remoteTags[i];
    }
    remote.addParameters(remoteInfos.data(), remoteInfos.size());
    Presonus::StormMuteGroupComponent component(state);
    component.addParameters(localInfos.data(), localInfos.size());
    auto id = [&](Parameter *p) {
      if (!p)
        return -1;
      for (int i = 0; i < 84; ++i)
        if (params[i].get() == p)
          return i;
      for (int t : localTags)
        if (component.getParameterByTag(t) == p)
          return 16 + t;
      for (int t : remoteTags)
        if (remote.getParameterByTag(t) == p)
          return 48 + t;
      return -99;
    };
    trace.clear();
    int result = -1;
    switch (method) {
    case 1:
      result = component.recallMutes(index, flag);
      break;
    case 2:
      component.onObserveredParamChanged(params[param].get(), msg);
      break;
    case 3:
      component.onCascadeStateChange(flag);
      break;
    case 4:
      component.onMuteChanged(params[param].get());
      break;
    case 5:
      component.groupWasStored(index);
      break;
    case 6:
      component.refreshGroups();
      break;
    case 7: {
      Presonus::UC::MessageAttributes message(messageMatch ? "presetMuteGroup"
                                                           : nullptr);
      message.set("presetMuteGroupIndex",
                  static_cast<Core::int64>(static_cast<std::int32_t>(index)));
      component.notify(message);
      break;
    }
    case 8:
      component.onIdle();
      break;
    case 9:
      component.setAll(flag);
      break;
    case 10:
      component.deactivate(index);
      break;
    default:
      return 2;
    }
    std::cout << "OBS {\"trace\":[";
    for (unsigned i = 0; i < trace.size(); ++i) {
      if (i)
        std::cout << ',';
      std::cout << trace[i];
    }
    std::cout << "],\"values\":[";
    for (int i = 0; i < 4; ++i) {
      if (i)
        std::cout << ',';
      std::cout << params[i]->v;
    }
    std::cout << "],\"loose\":";
    std::vector<int> ids;
    for (int i = 0; i < state.loose.count(); ++i)
      ids.push_back(id(state.loose[i]));
    list(std::cout, ids);
    std::cout << ",\"delayed_count\":" << state.delayed.count()
              << ",\"members\":[";
    for (int g = 0; g < 3; ++g) {
      if (g)
        std::cout << ',';
      ids.clear();
      for (int i = 0; i < groupStates[g].members.count(); ++i)
        ids.push_back(id(groupStates[g].members[i]));
      list(std::cout, ids);
    }
    std::cout << "],\"bindings\":[";
    for (int i = 0; i < 3; ++i) {
      if (i)
        std::cout << ',';
      std::cout << '[' << id(groupStates[i].active) << ','
                << id(groupStates[i].alternateStatus) << ']';
    }
    std::cout << "],\"stored\":" << int(g0.stored)
              << ",\"recalling\":" << int(state.recalling);
    if (method == 1)
      std::cout << ",\"result\":" << result;
    std::cout << "}\n";
  }
}
