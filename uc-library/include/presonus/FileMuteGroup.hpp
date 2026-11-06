#pragma once

#include "core/portable/coreattributes.h"
#include "core/portable/corecomponent.h"
#include "core/portable/corefilename.h"
#include "presonus/MuteGroupBase.hpp"

// Partial source port. Provider relationships are evidence-backed;
// these declarations do not establish firmware layouts or ARM ABI.
namespace Presonus {
class FileMuteGroup : public MuteGroupBase, public Core::Portable::Component {
public:
  // Independent template compatibility API for earlier findAttribute callers.
  // No recovered original default-constructor identity is claimed.
  template <
      class Compatibility = presonus::mute_group_port::UnboundCompatibility>
  FileMuteGroup()
      : MuteGroupBase(Compatibility{}), Core::Portable::Component(""),
        parameter_(nullptr) {}
  FileMuteGroup(Core::Portable::FileName filename,
                Core::Portable::Parameter *parameter,
                Mixer::MixerComponentBase &mixer);
  ~FileMuteGroup() override;
  void paramChanged(Core::Portable::Parameter *parameter, int message) override;
  // void is a source-port declaration; original return spelling is unresolved.
  // Uses the borrowed mixer saveServices.parameters tree; no ARM layout claim.
  void activate() override;
  void cacheMutes(const Core::Portable::Attributes &attributes);
  void portableSetReactivation(bool value) { reactivate_ = value; }
  bool portableReactivation() const { return reactivate_; }
  const Core::Portable::FileName &portableFilename() const { return filename_; }
  // Native arguments occupy r1/r2/r3, establishing an instance method. The
  // boolean source return is a port choice; original C++ return is unencoded.
  bool findAttribute(const Core::Portable::Attributes *attributes,
                     const char *path, const char *attribute);

private:
  bool storing_ = false, reactivate_ = false;
  Core::Portable::FileName filename_;
  Core::Portable::Parameter *parameter_;
};
} // namespace Presonus
