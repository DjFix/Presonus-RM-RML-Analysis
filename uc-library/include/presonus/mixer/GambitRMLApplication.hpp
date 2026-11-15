#pragma once
#include "presonus/uc/server_registrar.hpp"
namespace Presonus::Mixer {
// Stateless partial portable source port. No original base, constructor,
// lifecycle, object layout or ARM ABI claim. Output uses the existing canonical
// ServerInfo composition: original words +4/+12 map to strings[0]/strings[2].
// This correspondence is an intentional source-port adaptation, not layout
// proof.
class GambitRMLApplication {
public:
  struct SourcePortConstruction {};
  explicit GambitRMLApplication(SourcePortConstruction) {}
  // void is a provisional return choice; the original declaration is
  // unresolved.
  virtual void getNetworkSetup(unsigned short &port,
                               Presonus::UC::ServerInfo &info) const;
};
} // namespace Presonus::Mixer
