#pragma once
#include "core/public/corevector.h"
#include "presonus/uc/ServerComponent.hpp"
namespace Presonus::Mixer {
class DCALevelHandler;
// Intentional portable state: native destroys pointer-vector storage, then the
// Component base. Pointees are borrowed. Original layout/ARM ABI is unresolved.
class ChannelDCAComponent : public Presonus::UC::ServerComponent {
public:
  struct SourcePortConstruction {};
  explicit ChannelDCAComponent(SourcePortConstruction) {}
  ~ChannelDCAComponent() override;
  Core::Vector<DCALevelHandler *> &sourcePortHandlers() { return handlers_; }

private:
  Core::Vector<DCALevelHandler *> handlers_;
};
} // namespace Presonus::Mixer
