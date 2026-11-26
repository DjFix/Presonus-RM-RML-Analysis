#include "Shared.hpp"
#include "../../network_next_services/fixture_next_manager.hpp"
#include "presonus/color/MixerColorConverter.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include <array>
#include <bit>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <source_location>
#include <span>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
using namespace Presonus;
using namespace Core::Portable;
namespace {
void *trackedReceiver = nullptr;
unsigned deallocations = 0;
unsigned selectorCalls = 0;
extern std::int64_t clockTicks;
void require(bool condition,
             std::source_location loc = std::source_location::current()) {
  if (!condition)
    throw std::runtime_error("family replay at " + std::to_string(loc.line()));
}
template <class T> void names(const char *name) {
  for (const std::string prefix :
       {std::string{}, std::string{"pre-"}, std::string{"Aux"},
        std::string{"Ch"}, std::string{"FX"}, std::string(126, 'a')}) {
    for (int number = 0; number <= 4; ++number) {
      Component group;
      T *channel = new T;
      require(std::string(channel->getName()).empty());
      if (number) {
        for (int i = 1; i < number; ++i)
          group.addChild(new Component);
        group.addChild(channel);
      }
      require(channel->getNumber() == number);
      require(channel->sourcePortLevelMeter().getPeakHold() == 0.f);
      for (unsigned i = 0; i < 4; ++i)
        require(channel->sourcePortGainReductionMeter(i).getPeakHold() == 0.f);
      Core::CString128 label(prefix.c_str());
      channel->getDefaultName(label);
      std::cout << "name\t" << name << '\t' << prefix << '\t' << number << '\t'
                << label.str() << '\n';
      if (!number)
        delete channel;
    }
  }
}
template <class T> void lifecycle(const char *name) {
  T *heap = new T;
  trackedReceiver = heap;
  deallocations = 0;
  delete static_cast<SLChannelBase *>(heap);
  require(trackedReceiver == nullptr && deallocations == 1);
  alignas(T) std::array<std::byte, sizeof(T)> storage;
  T *placed = new (storage.data()) T;
  trackedReceiver = placed;
  deallocations = 0;
  placed->~T();
  require(deallocations == 0 && trackedReceiver == placed);
  trackedReceiver = nullptr;
  std::cout << "lifecycle\t" << name << "\t1\t0\n";
}
template <class T> void meters(const char *kind) {
  T channel;
  constexpr bool stereo = std::is_base_of_v<SLStereoChannel, T>;
  std::vector<MeterMaid *> meters{&channel.sourcePortLevelMeter()};
  for (unsigned i = 0; i < 4; ++i)
    meters.push_back(&channel.sourcePortGainReductionMeter(i));
  if constexpr (stereo)
    meters.push_back(&channel.sourcePortRightMeter());
  static constexpr ParamInfo info =
      PARAM_FLOAT(1, "meter", 0, 1, 0, .01f, nullptr, nullptr, 0, 0);
  std::vector<std::unique_ptr<NumericParam>> parameters;
  for (auto *meter : meters) {
    auto &a = parameters.emplace_back(std::make_unique<NumericParam>(info));
    auto *ap = a.get();
    auto &b = parameters.emplace_back(std::make_unique<NumericParam>(info));
    meter->bindParameters(ap, b.get());
  }
  auto reset = [&] {
    for (auto *meter : meters)
      meter->reset();
    for (auto &parameter : parameters)
      parameter->setValue(0.f, false);
  };
  auto values = [&] {
    for (auto &parameter : parameters)
      std::cout << '\t' << std::bit_cast<std::uint32_t>(parameter->getValue());
    std::cout << '\n';
  };
  const int keys[] = {1818588780, 1919247477, 1668441444,
                      1735550308, 1819436388, 0};
  if constexpr (stereo) {
    for (int key : keys) {
      reset();
      channel.updateStereoMeters(key, .25f, .75f);
      std::cout << kind << "-update\t" << key << '\t'
                << std::bit_cast<std::uint32_t>(.25f) << '\t'
                << std::bit_cast<std::uint32_t>(.75f);
      values();
    }
  } else {
    for (int key : keys)
      for (float level : {-.25f, 0.f, .25f, 1.25f}) {
        reset();
        channel.updateMeter(key, level);
        std::cout << kind << "-update\t" << key << '\t'
                  << std::bit_cast<std::uint32_t>(level);
        values();
      }
  }
  reset();
  if constexpr (stereo)
    channel.updateStereoMeters(keys[0], .25f, .75f);
  else
    for (int key : std::span(keys, 5))
      channel.updateMeter(key, .25f);
  for (int frame = 0; frame < 10; ++frame) {
    channel.idleMeters();
    std::cout << kind << "-idle\t" << frame;
    values();
  }
  if constexpr (!stereo) {
    reset();
    for (int key : std::span(keys, 5))
      channel.updateMeter(key, .25f);
    clockTicks = 0;
    channel.sourcePortIdleTimer().beginAction(-1.f);
    for (int milliseconds :
         {0, 24, 25, 49, 50, 75, 100, 125, 150, 175, 200, 225, 250}) {
      clockTicks = std::int64_t(milliseconds) * 1000000;
      channel.onIdle();
      std::cout << kind << "-periodic\t" << milliseconds;
      values();
    }
  }
}

std::int64_t clockTicks = 0;
struct Client final : UC::ClientImplementation {
  explicit Client(UC::INetworkManager &manager)
      : ClientImplementation(presonus::uc::ClientStatePortTag{}, manager, 17,
                             29) {}
  std::uint64_t getSystemTime() const override { return 1234; }
  int handleEvent(void *, const UC::Event &) override { std::abort(); }
  void updateLevels(const UC::MeterEvent &) override { std::abort(); }
  void receiveEvent(const UC::TimeCodeEvent &) override { std::abort(); }
  void receiveEvent(const UC::ParamEvent &) override { std::abort(); }
  void receiveEvent(const UC::MessageEvent &) override { std::abort(); }
  void receiveEvent(const UC::BinaryEvent &) override { std::abort(); }
  void receiveEvent(const UC::DebugEvent &) override { std::abort(); }
  void sendAllToServer() override { std::abort(); }
};
const std::vector<ParamInfo> &channelInfos() {
  static const auto infos = [] {
    std::vector<ParamInfo> result;
    const int tags[] = {3,   5,   6,   7,   8,   9,   10,  11,  12,  13,
                        17,  20,  18,  21,  22,  224, 225, 226, 227, 228,
                        229, 230, 231, 232, 233, 234, 235, 236, 237, 238,
                        239, 300, 301, 302, 303, 255, 256, 271, 272, 411};
    for (int tag : tags) {
      ParamInfo info{};
      info.type = tag == 3 ? ParamInfo::kColor : ParamInfo::kFloat;
      info.tag = tag;
      std::snprintf(info.name, sizeof(info.name), "p%d", tag);
      info.minValue = 0.f;
      info.maxValue = 1.f;
      info.deltaValue = .01f;
      info.defaultValue = (tag == 13 || tag == 21) ? 1.f : 0.f;
      result.push_back(info);
    }
    return result;
  }();
  return infos;
}
struct Observer : IMixerComponentObserver {
  std::vector<int> events;
  void onSelectionChanged() override { events.push_back(-1); }
  void onObjectChanged(ObjectChangeMessage m) override {
    events.push_back(static_cast<int>(m));
  }
};
void positive() {
  using namespace presonus::uc;
  CclFactoryRegistry registry;
  ParamEditFactoryCodec edit;
  ParamValueFactoryCodec value;
  ParamStringFactoryCodec text;
  ParamColorFactoryCodec color;
  edit.registerIn(registry.registry());
  value.registerIn(registry.registry());
  text.registerIn(registry.registry());
  color.registerIn(registry.registry());
  UC::EventFactory factory(registry.registry());
  EventDispatcherState ds;
  UC::EventDispatcher dispatcher(ds);
  NetworkManagerState networkState{dispatcher, factory};
  networkState.storeFlags = [](void *, UC::EventItem &, int flags) {
    require(flags == 0);
  };
  networkState.reportOversized = [](void *) { std::abort(); };
  FixtureNextManager manager(networkState);
  Client client(manager);
  MappableMixer mapped;
  MixerColorConverter converter;
  Observer observer;
  mapped.setColorConverter(&converter);
  presonus::mixer::MappableMixerAccess::observers(mapped).add(&observer);
  const ParamInfo selectionInfo =
      PARAM_FLOAT(13, "selected", 0, 1, 1, .01f, nullptr, nullptr, 0, 0);
  NumericParam otherSelection(selectionInfo), signalSelection(selectionInfo),
      slaveSelection(selectionInfo);
  UC::ClientRootComponent root;
  root.bindSourcePortParameterSender(client, edit, value, text, color);
  auto *groups = new Component("channels");
  root.addChild(groups);
  auto *line = new Component("line");
  groups->addChild(line);
  auto *signal = new Component("signalgen");
  groups->addChild(signal);
  MixerClientComponentBase mixer(*groups);
  mixer.bindSourcePortSelectionObservers(mapped);
  auto *left = new SLChannel;
  auto *right = new SLChannel;
  left->setName("left");
  right->setName("right");
  line->addChild(left);
  line->addChild(right);
  line->addChild(new SLChannel("other", &otherSelection));
  line->addChild(new Component("not-a-channel"));
  signal->addChild(new SLChannel("generator", &signalSelection));
  const auto &infos = channelInfos();
  left->addParameters(infos.data(), static_cast<int>(infos.size()));
  right->addParameters(infos.data(), static_cast<int>(infos.size()));
  left->bindSourcePortMixerObservers(mapped, mapped);
  right->bindSourcePortMixerObservers(mapped, mapped);
  unsigned queued = 0;
  auto drain = [&] {
    while (auto *item = ds.retrieve()) {
      require(item->getData().routeA == 17 && item->getData().routeB == 29);
      require(item->getData().type == 0x5056 ||
              item->getData().type == 0x5043 || item->getData().type == 0x5053);
      ++queued;
      delete item;
    }
  };
  clockTicks = 0;
  left->init(mixer, *right);
  drain();
  right->init(mixer, *left);
  drain();
  require(left->countParameters() == static_cast<int>(infos.size()) + 3);
  require(left->getSelectionParameter() == left->getParameterByTag(13));
  require(left->getLinkedSelectionParameter() == right->getParameterByTag(13));
  require(!left->getSelectionParameter()->isPublic());
  require(left->getParameterByTag(15000)->getValue() == 1.f);
  require(right->getParameterByTag(15000)->getValue() == 0.f);
  require(left->getLinkNeighbour() == right &&
          right->getLinkNeighbour() == left);
  require(left->isLinked() && right->isLinked());
  Core::Vector<Parameter *> slow;
  left->getSlowLinkParams(slow);
  require(slow.count() == 23);
  require(left->getLinkParameter() == left->getParameterByTag(21));
  require(left->getLinkMasterParameter() == left->getParameterByTag(22));
  require(left->getColorIndex() ==
          converter.getColorIndexForRGB(left->getColor()));
  for (unsigned i = 0; i < 4; ++i)
    require(left->sourcePortGainReductionMeter(i).getDecayDelta() == .025f);
  auto *source = left->getParameterByTag(17);
  auto *peer = right->getParameterByTag(17);
  source->beginEdit();
  source->setValue(.75f, true);
  source->endEdit();
  drain();
  require(peer->getValue() == .75f && client.hasParamChanged(peer, 100));
  {
    SLChannelBase::ParamLinker direct(mixer, *left, *right);
    auto *peerColor = right->getColorParameter();
    client.resetParamChanges(peerColor);
    auto *editingColor = left->getColorParameter();
    editingColor->beginEdit();
    direct.paramChanged(editingColor, Parameter::kChanged);
    editingColor->endEdit();
    require(client.hasParamChanged(peerColor, 100));
    for (int msg : {0, 1, 2, 4, 5}) {
      client.resetParamChanges(peer);
      source->beginEdit();
      direct.paramChanged(source, msg);
      source->endEdit();
      require(!client.hasParamChanged(peer, 100));
    }
  }

  client.resetParamChanges(peer);
  source->setValue(.875f, true);
  drain();
  require(peer->getValue() == .75f && !client.hasParamChanged(peer, 100));

  left->getLinkParameter()->setValue(0.f, false);
  drain();
  require(!left->isLinked());
  source->beginEdit();
  source->setValue(.5f, true);
  source->endEdit();
  drain();
  require(peer->getValue() == .75f);
  left->getLinkParameter()->setValue(1.f, false);
  drain();
  require(left->isLinked());
  left->updateLinkedSelection(true);
  drain();
  require(mixer.getSelectedChannel() == left);
  require(otherSelection.getValue() == 0.f &&
          signalSelection.getValue() == 1.f);
  require(right->getSelectionParameter()->getValue() == 1.f);
  right->getSelectionParameter()->setValue(0.f, true);
  drain();
  require(right->getSelectionParameter()->getValue() == 1.f &&
          mixer.getSelectedChannel() == right);
  observer.events.clear();
  left->getParameterByTag(256)->setValue(.25f, true);
  drain();
  require(observer.events == std::vector<int>{10});
  observer.events.clear();
  left->getParameterByTag(272)->setValue(.25f, true);
  drain();
  require(observer.events.empty());
  left->getParameterByTag(411)->setValue(.25f, false);
  drain();
  require(observer.events == std::vector<int>{10});
  observer.events.clear();
  left->getLinkMasterParameter()->setValue(.5f, false);
  drain();
  require(observer.events == std::vector<int>{9});
  left->updateMeter(1818588780, .8f);
  const auto before = left->getParameterByTag(5)->getValue();
  clockTicks = 24000000;
  left->onIdle();
  require(left->getParameterByTag(5)->getValue() == before);
  for (int frame = 1; frame <= 10; ++frame) {
    clockTicks = std::int64_t(frame) * 25000000;
    left->onIdle();
  }
  require(left->getParameterByTag(5)->getValue() < before);
  const auto timer =
      presonus::timing::DelayTimerAccess::get(left->sourcePortIdleTimer());
  require(timer.executing && timer.duration == 25 && timer.start == 250);
  // Positive owning ParamLinker cleanup, then a live source edit proves that
  // removed observers are not invoked through a stale destroyed linker.
  for (int i = 0; i < slow.count(); ++i) {
    auto *input = slow.at(i);
    input->beginEdit();
    input->setValue(.25f, true);
    input->endEdit();
    drain();
    require(right->getParameterByTag(input->getTag())->getValue() == .25f);
  }
  auto *isolated = new SLChannel("isolated", nullptr);
  isolated->addParameters(infos.data(), static_cast<int>(infos.size()));
  auto *linker = new SLChannelBase::ParamLinker(mixer, *left, *isolated);
  trackedReceiver = linker;
  deallocations = 0;
  delete linker;
  require(trackedReceiver == nullptr && deallocations == 1);
  using Linker = SLChannelBase::ParamLinker;
  alignas(Linker) std::array<std::byte, sizeof(Linker)> linkStorage;
  auto *placedLinker = new (linkStorage.data()) Linker(mixer, *left, *isolated);
  trackedReceiver = placedLinker;
  deallocations = 0;
  placedLinker->~Linker();
  require(trackedReceiver == placedLinker && deallocations == 0);
  trackedReceiver = nullptr;
  source->beginEdit();
  source->setValue(.625f, true);
  source->endEdit();
  drain();
  require(isolated->getParameterByTag(17)->getValue() == 0.f);
  delete isolated;
  Component slaveGroups;
  auto *slaveLine = new Component("line");
  slaveGroups.addChild(slaveLine);
  slaveLine->addChild(new SLChannel("slave", &slaveSelection));
  MixerClientComponentBase slave(slaveGroups), middle, child;
  mixer.portableState().slaveMixer = &slave;
  middle.setMasterMixer(&mixer);
  child.setMasterMixer(&middle);
  child.channelSelected(left);
  require(mixer.getSelectedChannel() == left &&
          slaveSelection.getValue() == 0.f);
  mixer.channelSelected(nullptr);
  require(mixer.getSelectedChannel() == nullptr);
  const auto eventCount = observer.events.size();
  mixer.channelSelected(nullptr);
  require(observer.events.size() == eventCount);
  require(queued > 0);
  std::cout << "positive initialized CCL trees, real sender queue/cache, "
               "paired observer edits/removal, selection master/slave, real "
               "Mappable notifications, 25ms timer/ballistic pipeline passed\n";
  presonus::mixer::MappableMixerAccess::observers(mapped).empty();
}

template <class T> void initialization(const char *name) {
  MappableMixer mapped;
  MixerColorConverter converter;
  mapped.setColorConverter(&converter);
  Component groups;
  auto *line = new Component("line");
  groups.addChild(line);
  auto *channel = new T;
  auto *peer = new SLChannel;
  line->addChild(channel);
  line->addChild(peer);
  const auto &infos = channelInfos();
  channel->addParameters(infos.data(), static_cast<int>(infos.size()));
  peer->addParameters(infos.data(), static_cast<int>(infos.size()));
  MixerClientComponentBase mixer(groups);
  mixer.bindSourcePortSelectionObservers(mapped);
  channel->bindSourcePortMixerObservers(mapped, mapped);
  clockTicks = 0;
  channel->init(mixer, *peer);
  std::vector<std::uint32_t> rates;
  channel->sourcePortLevelMeter().setLevel(1.f);
  rates.push_back(std::bit_cast<std::uint32_t>(
      channel->sourcePortLevelMeter().getDecayDelta()));
  for (unsigned i = 0; i < 4; ++i)
    rates.push_back(std::bit_cast<std::uint32_t>(
        channel->sourcePortGainReductionMeter(i).getDecayDelta()));
  std::int64_t rightRate = -1;
  if constexpr (std::is_base_of_v<SLStereoChannel, T>) {
    channel->sourcePortRightMeter().setLevel(1.f);
    rightRate = std::bit_cast<std::uint32_t>(
        channel->sourcePortRightMeter().getDecayDelta());
  }
  Core::Vector<Parameter *> slow;
  channel->getSlowLinkParams(slow);
  unsigned mirrored = 0, unmirrored = 0;
  for (int i = 0; i < slow.count(); ++i) {
    auto *parameter = slow.at(i);
    auto *neighbour = peer->getParameterByTag(parameter->getTag());
    parameter->beginEdit();
    parameter->setValue(.25f, true);
    parameter->endEdit();
    if (neighbour->getValue() == .25f)
      ++mirrored;
    else {
      require(neighbour->getValue() == 0.f);
      ++unmirrored;
    }
  }
  constexpr bool base = std::is_same_v<SLChannelBase, T>;
  constexpr bool noLinker = std::is_same_v<SLRackStereoLineComponent, T>;
  require(channel->getLinkNeighbour() == (noLinker ? nullptr : peer));
  require(channel->getChannelType() == static_cast<ChannelType>(0));
  require(channel->getParameterByTag(15002));
  if constexpr (!base) {
    require(channel->getSelectionParameter()->getTag() == 13 &&
            !channel->getSelectionParameter()->isPublic());
    require(channel->getLinkedSelectionParameter() ==
            peer->getParameterByTag(13));
  }
  std::cout << "init\t" << name;
  for (auto rate : rates)
    std::cout << '\t' << rate;
  std::cout << '\t' << rightRate << '\t' << (!noLinker) << "\t1\t15002\t"
            << (base ? -1 : 13) << '\t' << (base ? -1 : 0) << '\t'
            << (base ? -1 : 13) << '\t'
            << std::bit_cast<std::uint32_t>(
                   channel->getParameterByTag(15000)->getValue())
            << '\t' << slow.count() << '\t' << unmirrored << '\n';
  if constexpr (base)
    require(mirrored == 0 && unmirrored == 0);
  else if constexpr (noLinker)
    require(mirrored == 0 && unmirrored == 23);
  else
    require(mirrored == 23 && unmirrored == 0);
}
struct LinkView : SLChannelBase {
  Parameter *parameter = nullptr;
  Parameter *getLinkParameter() const override { return parameter; }
};
void linkedGetters() {
  const ParamInfo info =
      PARAM_FLOAT(21, "linked", -1, 1, 0, .01f, nullptr, nullptr, 0, 0);
  NumericParam value(info);
  MixerClientComponentBase mixer;
  LinkView source;
  SLChannelBase peer;
  source.parameter = &value;
  for (float level : {-.25f, 0.f, .75f}) {
    value.setValue(level, false);
    SLChannelBase::ParamLinker linker(mixer, source, peer);
    std::cout << "linked\t" << std::bit_cast<std::uint32_t>(level) << '\t'
              << linker.isLinked() << '\n';
  }
  source.parameter = nullptr;
  SLChannelBase::ParamLinker linker(mixer, source, peer);
  require(!linker.isLinked());
  std::cout << "linked\tnull\t0\n";
}

std::string messageList(const Observer &observer) {
  std::string result;
  for (int v : observer.events) {
    if (!result.empty())
      result += ',';
    result += std::to_string(v);
  }
  return result.empty() ? "none" : result;
}
void callbackCase(const std::string &kind, int tag, int msg, bool master,
                  float selection = 1.f, float linked = 1.f,
                  bool missing = false, int notify = 0) {
  MappableMixer localMapped, masterMapped;
  Observer localObserver, masterObserver;
  presonus::mixer::MappableMixerAccess::observers(localMapped)
      .add(&localObserver);
  presonus::mixer::MappableMixerAccess::observers(masterMapped)
      .add(&masterObserver);
  Component groups;
  auto *line = new Component("line");
  groups.addChild(line);
  auto *channel = new SLChannel;
  auto *peer = new SLChannel;
  line->addChild(channel);
  line->addChild(peer);
  const auto &infos = channelInfos();
  channel->addParameters(infos.data(), static_cast<int>(infos.size()));
  peer->addParameters(infos.data(), static_cast<int>(infos.size()));
  MixerClientComponentBase mixer(groups), masterMixer;
  mixer.bindSourcePortSelectionObservers(localMapped);
  masterMixer.bindSourcePortSelectionObservers(masterMapped);
  channel->bindSourcePortMixerObservers(localMapped,
                                        master ? masterMapped : localMapped,
                                        master ? &masterMapped : nullptr);
  clockTicks = 0;
  channel->init(mixer, *peer);
  channel->getSelectionParameter()->setValue(selection, false);
  channel->getLinkParameter()->setValue(linked, false);
  peer->getParameterByTag(13)->setValue(0.f, false);
  if (master)
    mixer.setMasterMixer(&masterMixer);
  if (missing)
    channel->bindLinkedSelectionParameter(nullptr);
  localObserver.events.clear();
  masterObserver.events.clear();
  selectorCalls = 0;
  if (kind == "linked")
    channel->updateLinkedSelection(notify);
  else if (kind == "base")
    channel->SLChannelBase::paramChanged(channel->getParameterByTag(tag), msg);
  else
    channel->paramChanged(channel->getParameterByTag(tag), msg);
  std::cout << "callback\t" << kind << '\t' << tag << '\t' << msg << '\t'
            << master << '\t' << std::bit_cast<std::uint32_t>(selection) << '\t'
            << std::bit_cast<std::uint32_t>(linked) << '\t' << missing << '\t'
            << notify << '\t'
            << std::bit_cast<std::uint32_t>(
                   channel->getSelectionParameter()->getValue())
            << '\t'
            << std::bit_cast<std::uint32_t>(
                   peer->getParameterByTag(13)->getValue())
            << '\t' << selectorCalls << '\t' << messageList(localObserver)
            << '\t' << messageList(masterObserver) << '\n';
}
void callbacks() {
  const std::pair<int, int> pairs[] = {{13, 2},  {21, 2},  {22, 2},  {17, 2},
                                       {21, 3},  {22, 3},  {3, 3},   {15002, 3},
                                       {17, 3},  {13, 0},  {13, 4},  {411, 3},
                                       {255, 2}, {256, 2}, {271, 2}, {272, 2}};
  for (const std::string kind : {"base", "channel"}) {
    for (auto [tag, msg] : pairs) {
      callbackCase(kind, tag, msg, false);
      if (tag == 3 || tag == 256)
        callbackCase(kind, tag, msg, true);
    }
    callbackCase(kind, 21, 3, false, 0.f);
  }
  for (int notify : {0, 1})
    for (float link : {0.f, 1.f})
      for (bool missing : {false, true})
        callbackCase("linked", 0, 0, false, 1.f, link, missing, notify);
}

struct SelectorGroup : Component {
  using Component::Component;
  void addNull() { children.add(nullptr); }
  void removeNull() { children.remove(nullptr); }
};
struct ParameterNotice : ParamObserverBase {
  std::vector<int> &output;
  int index;
  ParameterNotice(std::vector<int> &o, int i) : output(o), index(i) {}
  void paramChanged(Parameter *, int msg) override {
    if (msg == Parameter::kChanged)
      output.push_back(index);
  }
};
struct SelectorObserver : IMixerComponentObserver {
  int id;
  MappableMixer &mapped;
  std::vector<std::string> &output;
  bool mutate = false;
  IMixerComponentObserver *replacement = nullptr;
  SelectorObserver(int i, MappableMixer &m, std::vector<std::string> &o)
      : id(i), mapped(m), output(o) {}
  void onSelectionChanged() override {
    output.push_back("S" + std::to_string(id));
    if (mutate) {
      auto &v = presonus::mixer::MappableMixerAccess::observers(mapped);
      v.remove(this);
      v.add(replacement);
    }
  }
  void onObjectChanged(ObjectChangeMessage msg) override {
    output.push_back("O" + std::to_string(id) + ":" +
                     std::to_string(static_cast<int>(msg)));
  }
};
void selectorCase(int depth, bool slavePresent, const std::string &transition,
                  const std::string &relation, bool mutate) {
  std::vector<int> notices;
  std::vector<std::unique_ptr<ParameterNotice>> observers;
  const ParamInfo info =
      PARAM_FLOAT(13, "selection", 0, 1, 1, .01f, nullptr, nullptr, 0, 0);
  std::vector<std::unique_ptr<NumericParam>> parameters;
  for (int n = 0; n < 25; ++n) {
    parameters.push_back(std::make_unique<NumericParam>(info));
    observers.push_back(std::make_unique<ParameterNotice>(notices, n));
    parameters.back()->addObserver(observers.back().get());
  }
  Component rootGroups, slaveGroups;
  const char *names[] = {"line",  "return", "fxreturn", "talkback", "aux",
                         "fxbus", "sub",    "main",     "mono"};
  std::vector<SelectorGroup *> groups;
  std::vector<SLChannel *> roots;
  for (int role = 0; role < 2; ++role)
    for (int type = 0; type < 9; ++type) {
      auto *group = new SelectorGroup(names[type]);
      (role ? slaveGroups : rootGroups).addChild(group);
      groups.push_back(group);
      int index = role * 12 + type + 2;
      auto *channel = new SLChannel("channel", parameters[index].get());
      group->addChild(channel);
      if (!role)
        roots.push_back(channel);
    }
  auto *source = new SLChannel("source", relation == "selection_null" ||
                                                 relation == "both_null"
                                             ? nullptr
                                             : parameters[0].get());
  auto *peer = new SLChannel("peer", parameters[1].get());
  source->bindLinkedSelectionParameter(
      relation == "linked_null" || relation == "both_null"
          ? nullptr
          : parameters[relation == "same" ? 0 : 1].get());
  groups[0]->insertChildAt(0, source);
  groups[0]->insertChildAt(1, peer);
  groups[0]->addNull();
  groups[0]->addChild(new Component("wrong-type"));
  auto *signal = new Component("signalgen");
  rootGroups.addChild(signal);
  signal->addChild(new SLChannel("signal", parameters[24].get()));
  SLChannelBase *initial =
      transition == "same" || transition == "clear" || transition == "other"
          ? source
          : nullptr;
  SLChannelBase *incoming = transition == "null" || transition == "clear"
                                ? nullptr
                            : transition == "other" ? roots[1]
                                                    : source;
  MixerClientComponentBase rootMixer(rootGroups, initial),
      slaveMixer(slaveGroups), middle, child;
  middle.setMasterMixer(&rootMixer);
  child.setMasterMixer(&middle);
  rootMixer.portableState().slaveMixer = slavePresent ? &slaveMixer : nullptr;
  MappableMixer mapped;
  std::vector<std::string> messages;
  SelectorObserver one(1, mapped, messages), two(2, mapped, messages);
  one.mutate = mutate;
  one.replacement = &two;
  presonus::mixer::MappableMixerAccess::observers(mapped).add(&one);
  rootMixer.bindSourcePortSelectionObservers(mapped);
  auto *start = depth == 0 ? &rootMixer : depth == 1 ? &middle : &child;
  start->channelSelected(incoming);
  const auto firstMessages = messages;
  const auto firstNotices = notices;
  start->channelSelected(incoming);
  require(messages == firstMessages && notices == firstNotices);
  if (transition != "null")
    require(rootMixer.getSelectedChannel() == incoming);
  std::cout << "selector\t" << depth << '\t' << slavePresent << '\t'
            << transition << '\t' << relation << '\t' << mutate;
  const int indices[] = {0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10,
                         14, 15, 16, 17, 18, 19, 20, 21, 22, 24};
  for (int index : indices)
    std::cout << '\t'
              << std::bit_cast<std::uint32_t>(parameters[index]->getValue());
  std::cout << '\t';
  for (std::size_t n = 0; n < messages.size(); ++n) {
    if (n)
      std::cout << ',';
    std::cout << messages[n];
  }
  if (messages.empty())
    std::cout << "none";
  std::cout << '\t';
  for (std::size_t n = 0; n < notices.size(); ++n) {
    if (n)
      std::cout << ',';
    std::cout << notices[n];
  }
  if (notices.empty())
    std::cout << "none";
  std::cout << '\n';
  presonus::mixer::MappableMixerAccess::observers(mapped).empty();
  // Upstream Component destruction requires nonnull children; restore its
  // invariant after the intentional native-compatible null-roster input.
  groups[0]->removeNull();
}
void selectorCases() {
  for (int depth : {0, 1, 2})
    for (bool slave : {false, true})
      for (const std::string transition :
           {"null", "same", "select", "clear", "other"})
        selectorCase(depth, slave, transition, "distinct", false);
  for (const std::string relation :
       {"distinct", "same", "selection_null", "linked_null", "both_null"})
    for (bool mutate : {false, true})
      selectorCase(2, true, "select", relation, mutate);
}

void cascadeCases() {
  SLCascadeMeteringChannel channel, peer;
  static constexpr ParamInfo info =
      PARAM_FLOAT(1, "meter", 0, 1, 0, .01f, nullptr, nullptr, 0, 0);
  std::vector<MeterMaid *> meters{&channel.sourcePortLevelMeter()};
  for (unsigned i = 0; i < 4; ++i)
    meters.push_back(&channel.sourcePortGainReductionMeter(i));
  std::vector<std::unique_ptr<NumericParam>> parameters;
  for (auto *meter : meters) {
    auto *a =
        parameters.emplace_back(std::make_unique<NumericParam>(info)).get();
    auto *b =
        parameters.emplace_back(std::make_unique<NumericParam>(info)).get();
    meter->bindParameters(a, b);
  }
  auto run = [&](const std::string &method, bool master, int key, float level,
                 float slave) {
    for (auto *meter : meters)
      meter->reset();
    for (auto &p : parameters)
      p->setValue(0, false);
    channel.bindSourcePortMasterChannel(nullptr);
    channel.updateSlaveChannelLevel(slave);
    channel.updateAggregateMeter(0, 0.f);
    peer.updateSlaveChannelLevel(.5f);
    channel.bindSourcePortMasterChannel(master ? &peer : nullptr);
    if (method == "aggregate")
      channel.updateAggregateMeter(key, level);
    else if (method == "slave")
      channel.updateSlaveChannelLevel(level);
    else
      channel.slaveMixerChanged();
    std::cout
        << "cascade\t" << method << '\t' << master << '\t' << key << '\t'
        << std::bit_cast<std::uint32_t>(level) << '\t'
        << std::bit_cast<std::uint32_t>(slave) << '\t'
        << std::bit_cast<std::uint32_t>(channel.sourcePortLocalChannelLevel())
        << '\t'
        << std::bit_cast<std::uint32_t>(channel.sourcePortSlaveChannelLevel())
        << '\t'
        << std::bit_cast<std::uint32_t>(peer.sourcePortSlaveChannelLevel());
    for (auto &p : parameters)
      std::cout << '\t' << std::bit_cast<std::uint32_t>(p->getValue());
    std::cout << '\n';
  };
  const int keys[] = {1818588780, 1919247477, 1668441444,
                      1735550308, 1819436388, 0};
  for (bool master : {false, true})
    for (int key : keys)
      for (float level : {-.25f, .25f, 1.25f})
        for (float slave : {-.125f, .5f})
          run("aggregate", master, key, level, slave);
  for (float level : {-.25f, 0.f, .5f, 1.25f})
    run("slave", false, keys[0], level, .5f);
  run("changed", false, keys[0], .25f, .5f);
}

} // namespace
extern "C" std::int64_t __wrap__ZN8presonus4dice19packetClockRawTicksEv() {
  return clockTicks;
}
extern "C" void
__real__ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE(
    MixerClientComponentBase *, SLChannelBase *);
extern "C" void
__wrap__ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE(
    MixerClientComponentBase *mixer, SLChannelBase *channel) {
  ++selectorCalls;
  __real__ZN8Presonus24MixerClientComponentBase15channelSelectedEPNS_13SLChannelBaseE(
      mixer, channel);
}
extern "C" void __real__ZdlPv(void *);
extern "C" void __wrap__ZdlPv(void *address) {
  if (address && address == trackedReceiver) {
    ++deallocations;
    trackedReceiver = nullptr;
  }
  __real__ZdlPv(address);
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  const std::string mode(argv[1]);
  if (mode == "names") {
    names<SLChannelBase>("SLChannelBase");
    names<SLChannel>("SLChannel");
    names<SLCascadeMeteringChannel>("SLCascadeMeteringChannel");
    names<SLRackFXBusComponent>("SLRackFXBusComponent");
    names<SLRackFXReturnComponent>("SLRackFXReturnComponent");
    names<SLRackMonoBusComponent>("SLRackMonoBusComponent");
    names<SLRackMonoMainComponent>("SLRackMonoMainComponent");
    names<SLRackStereoMainComponent>("SLRackStereoMainComponent");
    names<SLRackTalkbackComponent>("SLRackTalkbackComponent");
  } else if (mode == "lifecycle") {
    lifecycle<SLChannelBase>("SLChannelBase");
    lifecycle<SLChannel>("SLChannel");
    lifecycle<SLStereoChannel>("SLStereoChannel");
    lifecycle<SLCascadeMeteringChannel>("SLCascadeMeteringChannel");
    lifecycle<SLRackFXBusComponent>("SLRackFXBusComponent");
    lifecycle<SLRackFXReturnComponent>("SLRackFXReturnComponent");
    lifecycle<SLRackMonoBusComponent>("SLRackMonoBusComponent");
    lifecycle<SLRackMonoMainComponent>("SLRackMonoMainComponent");
    lifecycle<SLRackStereoLineComponent>("SLRackStereoLineComponent");
    lifecycle<SLRackStereoMainComponent>("SLRackStereoMainComponent");
    lifecycle<SLRackTalkbackComponent>("SLRackTalkbackComponent");
  } else if (mode == "cascade") {
    cascadeCases();
  } else if (mode == "selector") {
    selectorCases();
  } else if (mode == "callbacks") {
    callbacks();
  } else if (mode == "init") {
    initialization<SLChannelBase>("SLChannelBase");
    initialization<SLChannel>("SLChannel");
    initialization<SLStereoChannel>("SLStereoChannel");
    initialization<SLRackStereoLineComponent>("SLRackStereoLineComponent");
    linkedGetters();
  } else if (mode == "positive") {
    positive();
  } else if (mode == "metering") {
    meters<SLChannelBase>("base");
    meters<SLRackStereoMainComponent>("stereo");
  } else
    return 2;
}
