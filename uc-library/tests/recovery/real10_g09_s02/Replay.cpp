#include "presonus/mixer/MixerComponent.hpp"
#include "presonus/mixer/NetworkSetupComponent.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/message_attributes.hpp"
#include "presonus/uc/mutable_message_event.hpp"
#include <iostream>
#include <stdexcept>
#include <string>
static presonus::uc::ClientTypedOrigins *origins;
static const Presonus::UC::Event *seen;
static int sends;
static unsigned type;
static std::string payload;
static std::string hex(const std::string &s) {
  static const char d[] = "0123456789abcdef";
  std::string r;
  for (unsigned char c : s) {
    r += d[c >> 4];
    r += d[c & 15];
  }
  return r.empty() ? "_" : r;
}
static std::string decode(const std::string &s) {
  if (s == "_" || s == "-")
    return "";
  std::string r;
  for (std::size_t i = 0; i < s.size(); i += 2)
    r += static_cast<char>(std::stoi(s.substr(i, 2), nullptr, 16));
  return r;
}
extern "C" int
__real__ZN8Presonus5Mixer21NetworkSetupComponent9sendEventERNS_2UC5EventE(
    Presonus::Mixer::NetworkSetupComponent *, Presonus::UC::Event &);
extern "C" int
__wrap__ZN8Presonus5Mixer21NetworkSetupComponent9sendEventERNS_2UC5EventE(
    Presonus::Mixer::NetworkSetupComponent *receiver,
    Presonus::UC::Event &event) {
  auto *message = origins->get<Presonus::UC::MessageEvent>(&event);
  if (!message || &message->header != &event ||
      (!message->data && message->sizeBits))
    throw std::logic_error("message payload provenance lost");
  ++sends;
  seen = &event;
  type = event.type;
  payload.assign(static_cast<const char *>(message->data), message->sizeBits);
  int result =
      __real__ZN8Presonus5Mixer21NetworkSetupComponent9sendEventERNS_2UC5EventE(
          receiver, event);
  if (result != 0)
    throw std::logic_error("disconnected provider returned nonzero");
  return result;
}
struct NetworkServices final : presonus::mixer::NetworkSetupServices {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected disconnected network service call");
  }
  int itemKind(const Presonus::UC::NetworkItem &) const override { fail(); }
  int itemFilter(const Presonus::UC::NetworkItem &) const override { fail(); }
  const char *itemName(const Presonus::UC::NetworkItem &) const override {
    fail();
  }
  const char *itemSerial(const Presonus::UC::NetworkItem &) const override {
    fail();
  }
  void itemTitle(const Presonus::UC::NetworkItem &,
                 Core::CStringBuffer<128> &) const override {
    fail();
  }
  Presonus::UC::ClientRootComponent *
  component(const Presonus::UC::NetworkItem &) const override {
    fail();
  }
  Presonus::UC::ClientImplementation &
  eventSender(Presonus::UC::ClientRootComponent &) const override {
    fail();
  }
  void acquire(Presonus::UC::NetworkItem &) override { fail(); }
  void release(Presonus::UC::NetworkItem &, bool) override { fail(); }
  void *mixerForClient(Presonus::UC::ClientRootComponent &) override { fail(); }
  void setRemoteMixer(void *) override { fail(); }
  void remoteIdle() override { fail(); }
  void restoredSelection() override { fail(); }
  void serverParamChanged(Core::Portable::Parameter *, int) override { fail(); }
};
struct UnusedMixerServices final
    : presonus::mixer_component_port::MixerServices {
  [[noreturn]] static void fail() {
    throw std::logic_error("unexpected Mixer service call");
  }
  void serverParamChanged(Presonus::Mixer::MixerComponent &,
                          Core::Portable::Parameter *, int) override {
    fail();
  }
  Core::Portable::Component &
  parameterComponent(Presonus::Mixer::ChannelComponent &) const override {
    fail();
  }
  Presonus::LinkableComponent *
  linkIdentity(Presonus::Mixer::ChannelComponent *) const override {
    fail();
  }
  const Core::Portable::IStorageFilter *storageFilter(int, bool) override {
    fail();
  }
  void load(const Core::Portable::InputStorage &) override { fail(); }
  void save(Core::Portable::OutputStorage &) override { fail(); }
  bool muteExcluded(const Presonus::Mixer::ChannelComponent &) const override {
    fail();
  }
  Core::Portable::Parameter &
  muteSource(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  Core::Portable::Parameter &
  muteDestination(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  Core::Portable::Parameter &
  selection(Presonus::Mixer::ChannelComponent &) override {
    fail();
  }
  const char *
  presetType(const Presonus::Panel::PresetComponent &) const override {
    fail();
  }
  void command(const char *, const char *, int) override { fail(); }
};
int main(int argc, char **argv) {
  const bool provider = argc == 2 && std::string(argv[1]) == "--provider";
  int mode, slot, eventType, hint;
  std::string idToken, componentToken, urlToken, slotKeyToken,
      componentKeyToken;
  while (std::cin >> mode >> idToken >> componentToken >> slot >> urlToken >>
         slotKeyToken >> componentKeyToken >> eventType >> hint) {
    sends = 0;
    seen = nullptr;
    type = 0;
    payload.clear();
    const auto id = decode(idToken), component = decode(componentToken),
               url = decode(urlToken), slotKey = decode(slotKeyToken),
               componentKey = decode(componentKeyToken);
    const char *idPtr = idToken == "-" ? nullptr : id.c_str();
    const char *componentPtr =
        componentToken == "-" ? nullptr : component.c_str();
    presonus::uc::ClientTypedOrigins registry;
    origins = &registry;
    Core::Portable::Component parameters("network");
    NetworkServices networkServices;
    presonus::mixer::NetworkSetupState networkState{parameters,
                                                    networkServices};
    Presonus::Mixer::NetworkSetupComponent network(networkState);
    presonus::mixer_component_port::MixerState state;
    state.stageboxNetwork = mode == 2 ? &network : nullptr;
    state.stageboxOrigins = &registry;
    UnusedMixerServices services;
    Presonus::Mixer::MixerComponent mixer(state, services);
    if (!provider)
      mixer.sendStageboxSceneMsg(idPtr, componentPtr, slot);
    else if (mode == 2) {
      Presonus::UC::MessageAttributes attributes(idPtr);
      attributes.setURL(url.c_str());
      attributes.set(slotKey.c_str(), static_cast<Core::int64>(slot));
      attributes.set(componentKey.c_str(), componentPtr, false);
      Presonus::UC::MutableMessageEvent message(attributes, eventType, hint);
      Presonus::UC::MessageEvent outgoing =
          presonus::uc::MutableMessageEventPortAccess::event(message);
      auto bound = registry.bind(outgoing);
      if (!bound)
        throw std::logic_error("provider bind failed");
      network.sendEvent(outgoing.header);
    }
    bool retained = seen && registry.get<Presonus::UC::MessageEvent>(seen);
    std::cout << "RESULT " << sends << ' ' << type << ' ' << hex(payload) << ' '
              << retained << '\n';
  }
}
