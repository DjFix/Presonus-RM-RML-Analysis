#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/coreparams.h"
#include "core/portable/corestorage.h"
#include <array>
#include <vector>
namespace Presonus {
namespace Dsp {
class IController;
}
namespace dspcomponent_port {
// Independent app state translated from reviewed constructor writes. No native
// offsets, original field declarations or inheritance are asserted.
struct LifecycleState {
  bool serverFlag = false;
  bool baseFlag = true;
  bool targetedFlag = false;
  bool slave = false;
  bool enabled = true;
  void *partner = nullptr;
};
// Explicit application dependency contract, independent of the original vtable.
struct Boundary {
  virtual ~Boundary() = default;
  virtual int count(Dsp::IController &) = 0;
  virtual float value(Dsp::IController &, int) = 0;
  virtual void set(Dsp::IController &, int, float) = 0;
  virtual unsigned flags(Dsp::IController &) = 0;
  virtual void acknowledge(Dsp::IController &) = 0;
  virtual bool readout(Dsp::IController &, int) = 0;
  virtual int load(const Core::Portable::InputStorage &) = 0;
  virtual void idle() = 0;
  virtual void changed(Core::Portable::Parameter *, int) = 0;
};
} // namespace dspcomponent_port
// Portable source model; original inheritance, layout and ordinary return
// declarations remain unresolved. Core parameters are the actual CCL provider.
class DspComponent {
public:
  DspComponent(const char *, Dsp::IController *);
  Dsp::IController *getController();
  void construct();
  bool isDspParameter(Core::Portable::Parameter *) const;
  void *castTo(int);
  int load(const Core::Portable::InputStorage &);
  void syncReadouts();
  void onIdle();
  void paramChanged(Core::Portable::Parameter *, int);
  void syncValues(bool);
  void bind(dspcomponent_port::Boundary &b) { boundary_ = &b; }
  std::vector<Core::Portable::Parameter *> &parameters() { return parameters_; }
  void setForwarding(bool b) { forwarding_ = b; }
  unsigned readoutCount() const { return count_; }
  Core::Portable::Component &coreComponent() { return coreComponent_; }
  Core::Portable::Attributes &linkAttributes() { return linkAttributes_; }
  const dspcomponent_port::LifecycleState &lifecycleState() const {
    return lifecycle_;
  }

private:
  dspcomponent_port::Boundary &boundary() const;
  // Actual pinned providers own their construction and cleanup. Composition is
  // an intentional source port, not original inheritance or ARM layout.
  Core::Portable::Component coreComponent_;
  dspcomponent_port::LifecycleState lifecycle_;
  Core::Portable::Attributes linkAttributes_;
  const char *name_;
  Dsp::IController *controller_;
  dspcomponent_port::Boundary *boundary_ = nullptr;
  std::vector<Core::Portable::Parameter *> parameters_;
  std::array<Core::Portable::Parameter *, 10> readouts_{};
  unsigned count_ = 0;
  bool forwarding_ = false;
};
} // namespace Presonus
