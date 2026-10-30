#include "presonus/uc/client_event_values.hpp"
#include "presonus/uc/client_implementation.hpp"
#include "presonus/uc/client_typed_origins.hpp"
#include "presonus/uc/file_transfer_manager.hpp"
namespace Presonus::UC {
ClientImplementation::ClientImplementation(
    presonus::uc::ClientDispatchPortTag, INetworkManager &manager,
    IFileTransferManager &files, presonus::uc::EventOrigins &origins,
    presonus::uc::ClientTypedOrigins &typed, std::uint32_t routeA,
    std::uint32_t routeB)
    : manager_(manager), routeA_(routeA), routeB_(routeB), files_(&files),
      eventOrigins_(&origins), typedOrigins_(&typed) {}
ClientImplementation::~ClientImplementation() {
  manager_.unregisterHandler(this);
}
int ClientImplementation::connect(int server, MessageEvent &message) {
  routeB_ = static_cast<std::uint32_t>(server);
  manager_.setMulticastMapping(static_cast<int>(routeA_), server, 1,
                               static_cast<unsigned char>(untouchedBits_));
  untouchedBits_ = (untouchedBits_ & ~std::uint64_t{255}) | 1;
  return sendEvent(message.header);
}
int ClientImplementation::disconnect(MessageEvent *message) {
  if (message) {
    manager_.setMulticastMapping(static_cast<int>(routeA_),
                                 static_cast<int>(routeB_), 0,
                                 static_cast<unsigned char>(untouchedBits_));
    untouchedBits_ &= ~std::uint64_t{255};
    sendEvent(message->header);
  }
  // Fully injected service is a valid-domain prerequisite; the old state-only
  // tag remains usable for its retained eight methods, never disconnect.
  if (!files_)
    return -1;
  const int result = files_->cancelForHandler(static_cast<int>(routeA_), 0);
  routeB_ = 0;
  return result;
}
int ClientImplementation::handleEvent(void *context, const Event &event) {
  switch (event.type) {
  case 19778:
  case 19795:
    if (eventOrigins_)
      if (auto value = eventOrigins_->meter(&event)) {
        updateLevels(*value);
        return 0;
      }
    return -1;
  case 20547:
  case 20556:
  case 20562:
  case 20563:
  case 20566:
    if (eventOrigins_)
      if (auto value = eventOrigins_->param(&event)) {
        receiveEvent(*value);
        return 0;
      }
    return -1;
  case 21571:
    if (typedOrigins_)
      if (auto *value = typedOrigins_->get<TimeCodeEvent>(&event)) {
        receiveEvent(*value);
        return 0;
      }
    return -1;
  case 19021:
  case 21826:
  case 23106:
  case 23117:
    if (typedOrigins_)
      if (auto *value = typedOrigins_->get<MessageEvent>(&event)) {
        receiveEvent(*value);
        return 0;
      }
    return -1;
  case 16975:
    if (typedOrigins_)
      if (auto *value = typedOrigins_->get<BinaryEvent>(&event)) {
        receiveEvent(*value);
        return 0;
      }
    return -1;
  case 17474:
    if (typedOrigins_)
      if (auto *value = typedOrigins_->get<DebugEvent>(&event)) {
        receiveEvent(*value);
        return 0;
      }
    return -1;
  case 19538: {
    const LoopbackReplyEvent value{event};
    receiveEvent(value);
    return 0;
  }
  case 17985:
  case 17988:
  case 18003:
    return files_ ? files_->handleEvent(context, event) : -1;
  default:
    return manager_.handleEvent(context, event);
  }
}
} // namespace Presonus::UC
