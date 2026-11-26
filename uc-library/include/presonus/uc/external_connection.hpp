#pragma once
#include "presonus/uc/connection.hpp"

namespace presonus::uc {
// Independent configuration; offsets/inheritance of the original are not
// asserted. A nonnull callback represents an existing external handler.
struct ExternalConnectionState {
  std::uint32_t routeBits = 0;
  unsigned char orientation = 0;
  void *handlerContext = nullptr;
  int (*handle)(void *, void *origin, const Presonus::UC::Event &) = nullptr;
};
} // namespace presonus::uc
namespace Presonus::UC {
// Original RTTI-proven Connection base. Both original-named owning and
// independent borrowed source constructors retain explicit layout/ABI limits.
class ExternalConnection : public Connection {
public:
  ExternalConnection(presonus::uc::ExternalConnectionState &state,
                     presonus::uc::ConnectionState &common,
                     presonus::uc::BasicConnectionState &outgoing)
      : Connection(common, outgoing), state_(state) {}
  ExternalConnection(ConnectionHandler &, IDataChannel *);
  ~ExternalConnection() override;
  bool process(bool) override;
  void adjustRouting(Event &, bool) override;
  bool handleInternal(const Event &) override;
  int getType() const override;
  void getAddress(const char *&, unsigned short &) const override;

private:
  presonus::uc::ExternalConnectionState ownedState_;
  presonus::uc::ExternalConnectionState &state_;
};
} // namespace Presonus::UC
