#pragma once
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
};
} // namespace linkable_port
// Portable source model. Fields, inheritance and return declarations of the
// original ARM class remain unresolved. The explicit boundary is mandatory.
class LinkableComponent {
public:
  LinkableComponent(linkable_port::State &state,
                    linkable_port::Boundary &boundary)
      : state_(state), boundary_(boundary) {}
  void linkAsSlave(LinkableComponent &);
  void setLink(LinkableComponent &, bool);
  void removeLink();
  void setLinkEnabled(bool);
  bool isLinked() const;

private:
  linkable_port::State &state_;
  linkable_port::Boundary &boundary_;
};
} // namespace Presonus
