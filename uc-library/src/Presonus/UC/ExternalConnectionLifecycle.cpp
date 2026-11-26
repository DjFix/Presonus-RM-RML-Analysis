#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/external_connection.hpp"
#include "presonus/uc/report.hpp"
namespace Presonus::UC {
ExternalConnection::ExternalConnection(ConnectionHandler &handler,
                                       IDataChannel *channel)
    : Connection(handler, 3), state_(ownedState_) {
  presonus::uc::ConnectionSourceAccess::transport(*this).bind(channel);
}
ExternalConnection::~ExternalConnection() = default;
bool ExternalConnection::process(bool drain) {
  Connection::process(drain);
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  if (provider.channel && provider.channel->hasErrors(1)) {
    UCReportMessage(0, "External connection is in error state!!!", 0);
    provider.failed = true;
  }
  return !provider.failed;
}
} // namespace Presonus::UC
