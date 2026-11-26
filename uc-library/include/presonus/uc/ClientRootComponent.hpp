#pragma once

#include "presonus/uc/ClientComponent.hpp"
#include "presonus/uc/parameter_events.hpp"

namespace Core::Portable {
class Attributes;
}

namespace Presonus::UC {

class ClientImplementation;
struct BinaryEvent;
struct DebugEvent;
struct MeterEvent;
struct TimeCodeEvent;

// Portable primary-component subset. Transport and secondary interfaces are
// outside this class's recovered contract.
class ClientRootComponent : public ClientComponent {
public:
  static constexpr int kTypeID = 0x436c5274;
  static constexpr int __typeid() { return kTypeID; }
  using ClientComponent::ClientComponent;

  void *castTo(int typeId) override;
  ClientRootComponent *getRoot() override;
  void sendParamChange(ClientComponent &, Core::Portable::Parameter *, int);

  // Explicit source-port injection. These real providers and registered codecs
  // must outlive this root. No default singleton bootstrap or duplicated
  // sender.
  void
  bindSourcePortParameterSender(ClientImplementation &client,
                                presonus::uc::ParamEditFactoryCodec &edit,
                                presonus::uc::ParamValueFactoryCodec &value,
                                presonus::uc::ParamStringFactoryCodec &text,
                                presonus::uc::ParamColorFactoryCodec &color) {
    parameterClient_ = &client;
    editCodec_ = &edit;
    valueCodec_ = &value;
    textCodec_ = &text;
    colorCodec_ = &color;
  }
  ClientImplementation *sourcePortParameterClient() const {
    return parameterClient_;
  }
  void setSourcePortReceivingParameters(bool receiving) {
    receivingParameters_ = receiving;
  }
  void setSourcePortSendEditGestures(bool enabled) {
    sendEditGestures_ = enabled;
  }
  Core::abs_time getSystemTime() const;

  void receiveEvent(const BinaryEvent &);
  void receiveEvent(const DebugEvent &);
  void receiveEvent(const TimeCodeEvent &);
  void updateLevels(const MeterEvent &);
  void subscriptionReply(const MessageAttributes *);
  bool collectAll(Core::Portable::Attributes &, ClientComponent &) const;

private:
  ClientImplementation *parameterClient_ = nullptr;
  presonus::uc::ParamEditFactoryCodec *editCodec_ = nullptr;
  presonus::uc::ParamValueFactoryCodec *valueCodec_ = nullptr;
  presonus::uc::ParamStringFactoryCodec *textCodec_ = nullptr;
  presonus::uc::ParamColorFactoryCodec *colorCodec_ = nullptr;
  bool receivingParameters_ = false;
  bool sendEditGestures_ = false;
};

} // namespace Presonus::UC
