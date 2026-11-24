#include "presonus/uc/server.hpp"

namespace Presonus::UC {
LocalServer::LocalServer(int identifier, IEventHandler *handler,
                         const ServerInfo &info)
    : Server(), handler_(handler) {
  state_.identifierBits = static_cast<std::uint32_t>(identifier);
  state_.localRegistrationByte = 0;
  setInfo(info);
}
} // namespace Presonus::UC
