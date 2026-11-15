#pragma once
#include "core/portable/coreattributes.h"
#include "core/portable/corecomponent.h"
#include "core/portable/corestorage.h"
#include "core/system/corethread.h"
#include <cstddef>
#include <cstdint>

namespace Presonus {
class LinkableComponent;
namespace linkable_port {
// Independent application boundary, not a recovered vtable or Core provider.
struct Boundary {
  virtual ~Boundary() = default;
  virtual LinkableComponent *query(LinkableComponent &, std::uint32_t) = 0;
  virtual void remove(LinkableComponent &) = 0;
  virtual void set(LinkableComponent &, LinkableComponent &, bool) = 0;
  virtual void master(LinkableComponent &, LinkableComponent &) = 0;
};
struct State {
  LinkableComponent *partner = nullptr;
  std::uint8_t slave = 0;
  std::uint8_t enabled = 0;
  LinkableComponent *const *children = nullptr;
  std::size_t count = 0;
  // Actual pinned provider composition. This is portable state, not original
  // inheritance/layout. One process-wide storage lock mirrors the observed
  // shared lock identity; existing borrowed application boundaries stay intact.
  Core::Portable::Attributes alternate{
      Core::Portable::AttributeAllocator::getDefault()};
  Core::Portable::Component component{"LinkableComponent"};
  inline static Core::Threads::Lock alternateLock;
};
} // namespace linkable_port
// Portable source model. Fields, inheritance and return declarations of the
// original ARM class remain unresolved. The explicit boundary is mandatory.
class LinkableComponent {
public:
  LinkableComponent(linkable_port::State &state,
                    linkable_port::Boundary &boundary)
      : state_(state), boundary_(boundary) {}
  // Original ordinary returns remain declaration-pending.
  void toggleAltMemory();
  void copyToAltMemory(Core::Portable::Attributes &source);
  void loadAltMemory(const Core::Portable::InputStorage &storage);
  bool save(Core::Portable::OutputStorage &storage) const;
  void linkAsSlave(LinkableComponent &);
  void setLink(LinkableComponent &, bool);
  void removeLink();
  void setLinkEnabled(bool);
  bool isLinked() const;
  // Portable return choices; original declarations and ARM layout unresolved.
  std::uint8_t isLinkSlave() const;
  LinkableComponent *castTo(int);

private:
  linkable_port::State &state_;
  linkable_port::Boundary &boundary_;
};
} // namespace Presonus
