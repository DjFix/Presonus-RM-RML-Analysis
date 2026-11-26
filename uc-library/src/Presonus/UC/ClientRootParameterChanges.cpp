#include "presonus/uc/ClientRootComponent.hpp"
#include "presonus/uc/client_implementation.hpp"
#include <bit>

namespace Presonus::UC {
namespace {
template <class Codec, class Payload>
void sendBound(ClientImplementation &client, Codec &codec, Payload &payload) {
  codec.bind(payload);
  struct Unbind {
    Codec &codec;
    Payload &payload;
    ~Unbind() { codec.unbind(payload); }
  } unbind{codec, payload};
  client.sendEvent(payload.header);
}
} // namespace

void ClientRootComponent::sendParamChange(ClientComponent &component,
                                          Core::Portable::Parameter *parameter,
                                          int msg) {
  using Core::Portable::ColorParam;
  using Core::Portable::Parameter;
  using Core::Portable::ParamInfo;
  // A real attached Parameter is required by the native contract. The nullable
  // sender is an explicit source-port unbound policy, not a recovered default.
  if (!parameter->isPublic() || !parameterClient_)
    return;
  if (msg == Parameter::kEndEdit)
    parameterClient_->setLastParamChange(parameter);
  const bool gesture =
      msg == Parameter::kBeginEdit || msg == Parameter::kEndEdit;
  if (receivingParameters_ ||
      (msg != Parameter::kEdit && (!gesture || !sendEditGestures_)))
    return;
  Core::CString256 path;
  component.getParameterPath(path, parameter);
  if (gesture) {
    if (!editCodec_)
      return;
    ParamEditEvent event;
    event.header = {0x5045, 0x94, 0, 0};
    event.index = msg == Parameter::kBeginEdit ? 2 : 0;
    path.copyTo(event.path.data(), static_cast<int>(event.path.size()));
    sendBound(*parameterClient_, *editCodec_, event);
  } else if (parameter->getType() == ParamInfo::kString) {
    if (!textCodec_)
      return;
    ParamStringEvent event;
    event.header = {0x5053, 0x194, 0, 0};
    path.copyTo(event.path.data(), static_cast<int>(event.path.size()));
    parameter->toString(event.text.data(), static_cast<int>(event.text.size()));
    sendBound(*parameterClient_, *textCodec_, event);
  } else if (parameter->getType() == ParamInfo::kColor) {
    auto *color = ColorParam::cast(parameter);
    if (!color || !colorCodec_)
      return;
    ParamColorEvent event;
    event.header = {0x5043, 0x98, 0, 0};
    path.copyTo(event.path.data(), static_cast<int>(event.path.size()));
    event.colorBits = color->getColor();
    sendBound(*parameterClient_, *colorCodec_, event);
  } else {
    if (!valueCodec_)
      return;
    ParamValueEvent event;
    event.header = {0x5056, 0x98, 0, 0};
    path.copyTo(event.path.data(), static_cast<int>(event.path.size()));
    event.valueBits = std::bit_cast<std::uint32_t>(parameter->getNormalized());
    sendBound(*parameterClient_, *valueCodec_, event);
  }
}
} // namespace Presonus::UC
