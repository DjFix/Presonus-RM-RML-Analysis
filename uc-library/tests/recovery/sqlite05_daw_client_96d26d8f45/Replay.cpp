// Runtime replay assertions also run in release builds.
#undef NDEBUG

#include "core/public/coreformatter.h"
#include "presonus/DAWChannel.hpp"
#include "presonus/DAWChannelGroup.hpp"
#include "presonus/DAWClientComponent.hpp"
#include "presonus/DAWDeviceFolder.hpp"
#include "presonus/DAWDeviceSlot.hpp"
#include "presonus/IDAWDialogHandler.hpp"
#include "presonus/IDAWTimeInfo.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

extern "C" void
__real__ZN4Core17FormatterRegistry8optimizeEPPKc(Core::CStringPtr names[]);

extern "C" void
__wrap__ZN4Core17FormatterRegistry8optimizeEPPKc(Core::CStringPtr names[]) {
  for (unsigned index = 0; names[index]; ++index) {
    assert(index < 4);
    std::cout << names[index] << '\n';
  }
  __real__ZN4Core17FormatterRegistry8optimizeEPPKc(names);
}

using namespace Presonus;
using namespace Core::Portable;

namespace {

template <typename T>
unsigned identity(T *value, T *first, T *second = nullptr) {
  if (!value)
    return 0;
  if (value == first)
    return 1;
  assert(value == second);
  return 2;
}

struct Client : DAWClientComponent {
  using DAWClientComponent::dawFlags_;
  using DAWClientComponent::dialogHandler_;
  using DAWClientComponent::observers_;
  using DAWClientComponent::timeInfo_;
  using DAWClientComponent::timeInfoFactory_;

  mutable std::vector<std::string> names;
  Component *lookupOverride = nullptr;

  Component *findChild(const char *name) const override {
    names.emplace_back(name);
    if (lookupOverride)
      return lookupOverride;
    return Component::findChild(name);
  }
};

using Event = std::array<unsigned, 4>;

struct Observer : IDAWComponentObserver {
  Observer(unsigned index, Client &client, std::vector<Event> &events,
           DAWChannel *firstChannel, DAWChannel *secondChannel,
           DAWChannelGroup *group, DAWDeviceFolder *folder, DAWDeviceSlot *slot)
      : index(index), client(client), events(events),
        firstChannel(firstChannel), secondChannel(secondChannel), group(group),
        folder(folder), slot(slot) {}

  void onFocusChannelChanged() override {
    events.push_back(
        {0, index,
         identity(client.getFocusChannel(), firstChannel, secondChannel), 0});
  }

  void onChannelsChanged(DAWChannelGroup *value) override {
    events.push_back({1, index, identity(value, group), 0});
  }

  void onSlotCountChanged(DAWDeviceFolder *value) override {
    events.push_back({3, index, identity(value, folder), 0});
  }

  void onSlotEditChanged(DAWDeviceSlot *value, bool edit) override {
    events.push_back({4, index, identity(value, slot), edit});
  }

  void onObjectChanged(ObjectChangeMessage message) override {
    events.push_back(
        {7, index, static_cast<unsigned>(message), client.dawFlags_});
  }

  unsigned index;
  Client &client;
  std::vector<Event> &events;
  DAWChannel *firstChannel;
  DAWChannel *secondChannel;
  DAWChannelGroup *group;
  DAWDeviceFolder *folder;
  DAWDeviceSlot *slot;
};

void checkFormatters(Client &client) {
  // Each target displaces one of the first four built-in formatters.
  // Looking up the duplicate name exposes the changed registration order.
  static Core::IntFormatter sentinels[]{
      Core::IntFormatter(Core::IntFormatter::instance().getName()),
      Core::IntFormatter(Core::FloatFormatter::instance().getName()),
      Core::IntFormatter(Core::PercentFormatter::instance().getName()),
      Core::IntFormatter(Core::PercentFormatter::instance(1).getName())};
  static Core::IntFormatter targets[]{
      Core::IntFormatter("gain.db.value"), Core::IntFormatter("pan.100"),
      Core::IntFormatter("gain.0"), Core::IntFormatter("bpm.value")};
  for (auto &formatter : sentinels) {
    const auto *original = Core::FormatterRegistry::find(formatter.getName());
    assert(original && original != &formatter);
    Core::FormatterRegistry::add(&formatter);
    assert(Core::FormatterRegistry::find(formatter.getName()) == original);
  }
  for (auto &formatter : targets)
    Core::FormatterRegistry::add(&formatter);

  client.optimize();
  for (std::size_t i = 0; i < std::size(sentinels); ++i) {
    assert(Core::FormatterRegistry::find(sentinels[i].getName()) ==
           &sentinels[i]);
    assert(Core::FormatterRegistry::find(targets[i].getName()) == &targets[i]);
  }
}

struct ChildLookup {
  std::string_view method;
  const char *name;
  Component *(DAWClientComponent::*getter)() const;
};

constexpr ChildLookup childLookups[] = {
    {"getMixer", "mixer", &DAWClientComponent::getMixer},
    {"getControlLink", "controls", &DAWClientComponent::getControlLink},
    {"getDocument", "document", &DAWClientComponent::getDocument},
    {"getRecordDiskSpace", "recorddiskspace",
     &DAWClientComponent::getRecordDiskSpace},
    {"getSessionComponent", "session",
     &DAWClientComponent::getSessionComponent},
    {"getRecordPanelComponent", "recordpanel",
     &DAWClientComponent::getRecordPanelComponent},
    {"getMetronomeComponent", "metronome",
     &DAWClientComponent::getMetronomeComponent},
};

unsigned namedChild(Client &client, std::string_view method, unsigned mode) {
  for (const auto &entry : childLookups) {
    if (entry.method != method)
      continue;
    Component overrideChild("external");
    Component *ownedChild = nullptr;
    if (mode == 3)
      client.lookupOverride = &overrideChild;
    if (mode == 2) {
      ownedChild = new Component(entry.name);
      client.addChild(ownedChild);
    }
    if (mode == 1) {
      std::string wrong(entry.name);
      wrong[0] -= 'a' - 'A';
      client.addChild(new Component(wrong.c_str()));
    }
    auto *result = (client.*entry.getter)();
    client.lookupOverride = nullptr;
    assert(client.names.size() == 1);
    return identity(result, ownedChild, &overrideChild);
  }
  std::abort();
}

unsigned loopTag(Client &client, std::string_view method, unsigned mode) {
  static constexpr ParamInfo infos[] = {
      PARAM_FLOAT(0, "loop-start", 0, 30, 0, 0.01f, 0, 0, 0, 0),
      PARAM_FLOAT(1, "loop-end", 0, 30, 0, 0.01f, 0, 0, 0, 0)};
  const int tag = method == "getLoopEndParam" ? 1 : 0;
  if (mode == 1)
    client.addParameters(&infos[1 - tag], 1);
  if (mode == 2)
    client.addParameters(infos, 2);
  Parameter *result =
      tag == 0 ? client.getLoopStartParam() : client.getLoopEndParam();
  return identity(result, client.findParameter(infos[tag].name));
}

} // namespace

int main(int argc, char **argv) {
  assert(argc == 5);
  const std::string_view method(argv[1]);
  const auto number = [&](int i) {
    return static_cast<unsigned>(std::strtoul(argv[i], nullptr, 10));
  };
  const unsigned init = number(2), arg = number(3), count = number(4);
  Client client;
  DAWChannel first, second;
  DAWChannelGroup group;
  DAWDeviceFolder folder;
  DAWDeviceSlot slot;
  DAWChannel *const channels[]{nullptr, &first, &second};
  IDAWDialogHandler firstHandler, secondHandler;
  IDAWDialogHandler *const handlers[]{nullptr, &firstHandler, &secondHandler};
  presonus::dawtime::DispatchState firstState{}, secondState{};
  IDAWTimeInfo firstTime(firstState), secondTime(secondState);
  IDAWTimeInfo *const timeInfos[]{nullptr, &firstTime, &secondTime};
  // The native factory interface is outside this packet. These opaque typed
  // tokens represent distinct aligned addresses and are never dereferenced.
  std::array<std::max_align_t, 2> factoryStorage{};
  IDAWTimeInfoFactory *const factories[]{
      nullptr, reinterpret_cast<IDAWTimeInfoFactory *>(&factoryStorage[0]),
      reinterpret_cast<IDAWTimeInfoFactory *>(&factoryStorage[1])};
  const bool focus = method == "getFocusChannel" || method == "setFocusChannel";
  const bool flags = method == "isDAWProgressMode" ||
                     method == "setDAWProgress" ||
                     method == "sendObjectChangeMessage";
  if (focus)
    client.setFocusChannel(channels[init]);
  client.dawFlags_ = flags ? init : 0x12345001;
  client.timeInfo_ = timeInfos[method == "getTimeInfo" ? init : 1];
  client.dialogHandler_ = handlers[method == "setDialogHandler" ? init : 1];
  Client::timeInfoFactory_ =
      factories[method == "setTimeInfoFactory" ? init : 1];

  std::vector<Event> events;
  const std::array<unsigned, 3> insertionOrder{2, 0, 1};
  std::array<Observer, 3> observers{{
      {0, client, events, &first, &second, &group, &folder, &slot},
      {1, client, events, &first, &second, &group, &folder, &slot},
      {2, client, events, &first, &second, &group, &folder, &slot},
  }};
  for (unsigned i = 0; i < count; ++i)
    assert(client.addSourcePortObserver(observers[insertionOrder[i]]));

  unsigned result = 0;
  if (method == "castTo")
    result = identity(client.castTo(static_cast<int>(arg)),
                      static_cast<void *>(&client));
  else if (method == "getFocusChannel")
    result = identity(client.getFocusChannel(), &first, &second);
  else if (method == "setFocusChannel")
    client.setFocusChannel(channels[arg]);
  else if (method == "channelsChanged")
    client.channelsChanged(arg ? &group : nullptr);
  else if (method == "slotCountChanged")
    client.slotCountChanged(arg ? &folder : nullptr);
  else if (method == "slotEditChanged")
    client.slotEditChanged(arg & 1 ? &slot : nullptr, arg & 2);
  else if (method == "sendObjectChangeMessage")
    client.sendObjectChangeMessage(
        static_cast<IDAWComponentObserver::ObjectChangeMessage>(arg));
  else if (method == "isDAWProgressMode")
    result = client.isDAWProgressMode();
  else if (method == "setDAWProgress")
    client.setDAWProgress(arg);
  else if (method == "getLoopStartParam" || method == "getLoopEndParam")
    result = loopTag(client, method, init);
  else if (method == "setDialogHandler")
    client.setDialogHandler(handlers[arg]);
  else if (method == "getTimeInfo")
    result = identity(client.getTimeInfo(), &firstTime, &secondTime);
  else if (method == "setTimeInfoFactory")
    Client::setTimeInfoFactory(factories[arg]);
  else if (method == "optimize")
    checkFormatters(client);
  else
    result = namedChild(client, method, init);

  assert(client.observers_.count() == static_cast<int>(count));
  for (unsigned i = 0; i < count; ++i)
    assert(client.observers_.at(i) == &observers[insertionOrder[i]]);
  assert(client.timeInfo_ == timeInfos[method == "getTimeInfo" ? init : 1]);
  const Client &observed = client;
  std::cout << result << ' '
            << identity(client.getFocusChannel(), &first, &second) << ' '
            << observed.dawFlags_ << ' '
            << identity(client.dialogHandler_, &firstHandler, &secondHandler)
            << ' '
            << identity(Client::timeInfoFactory_, factories[1], factories[2])
            << '\n';
  for (const auto &[slotId, observer, value, state] : events)
    std::cout << slotId << ' ' << observer << ' ' << value << ' ' << state
              << '\n';
  for (const auto &name : client.names)
    std::cout << name << '\n';
  return 0;
}
