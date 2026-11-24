#pragma once

#include "core/portable/corecomponent.h"
#include "core/public/gui/corecolor.h"

namespace Presonus {
class MixerClientComponentBase;
class MappableMixer;
enum ChannelType : int;
// Source-port inheritance and type ID: intentional CCL5 typed-object
// adaptation, not a claim about original ARM layout, private declarations or
// RTTI identity.
class SLChannelBase : public Core::Portable::Component {
public:
  DECLARE_CORE_CLASS(0x534c4342, SLChannelBase, Core::Portable::Component)
  using Core::Portable::Component::Component;
  virtual Core::Portable::Parameter *getSelectionParameter() const;
  // These nullable Parameter returns are intentional source-port declarations.
  // Original ARM bodies return zero without instance access. Their ordinary
  // return declarations/pointee qualifiers and original vtable layout remain
  // unresolved; matching method names do not establish ARM ABI compatibility.
  virtual Core::Portable::Parameter *getLinkParameter() const;
  virtual Core::Portable::Parameter *getColorParameter() const;
  virtual Core::Portable::Parameter *getLinkMasterParameter() const;
  virtual Core::Portable::Parameter *getLinkedSelectionParameter() const;
  // Independent borrowed input used by the portable color-index query.
  void bindColorIndexParameter(const Core::Portable::NumericParam *parameter) {
    colorIndexParameter_ = parameter;
    writableColorIndexParameter_ = nullptr;
  }
  // Separate source-port bindings preserve read-only index callers. Providers
  // are borrowed and must outlive this channel.
  void
  bindWritableColorIndexParameter(Core::Portable::NumericParam &parameter) {
    colorIndexParameter_ = &parameter;
    writableColorIndexParameter_ = &parameter;
  }
  void bindSourcePortColorMixer(const MappableMixer *mixer) {
    colorMixer_ = mixer;
  }
  void updateColorIndex();
  void updateColorFromIndex();
  int getColorIndex() const;
  Core::Color getColor() const;
  int getNumber() const;
  // Independent borrowed source binding. The mixer must outlive this channel.
  void bindSourcePortMixer(const MixerClientComponentBase *mixer) {
    sourcePortMixer_ = mixer;
  }
  ChannelType getChannelType() const;
  // The base leaves the supplied vector unchanged. The exact original return
  // declaration and vtable layout remain unresolved.
  virtual void
  getSlowLinkParams(Core::Vector<Core::Portable::Parameter *> &) const;

private:
  const Core::Portable::NumericParam *colorIndexParameter_ = nullptr;
  const MixerClientComponentBase *sourcePortMixer_ = nullptr;
  Core::Portable::NumericParam *writableColorIndexParameter_ = nullptr;
  const MappableMixer *colorMixer_ = nullptr;
};

class SLChannel : public SLChannelBase {
public:
  // Independent source-only setup; the initialized parameter is borrowed and
  // must outlive this channel. No original constructor/lifecycle credit.
  SLChannel(const char *name, Core::Portable::Parameter *selection)
      : SLChannelBase(name), selection_(selection) {}
  Core::Portable::Parameter *getSelectionParameter() const override;
  Core::Portable::Parameter *getColorParameter() const override;
  Core::Portable::Parameter *getLinkedSelectionParameter() const override;
  // Borrowed parameters must outlive use by this channel.
  void bindColorParameter(Core::Portable::Parameter *parameter) {
    color_ = parameter;
  }
  void bindLinkedSelectionParameter(Core::Portable::Parameter *parameter) {
    linkedSelection_ = parameter;
  }

private:
  Core::Portable::Parameter *selection_;
  Core::Portable::Parameter *color_ = nullptr;
  Core::Portable::Parameter *linkedSelection_ = nullptr;
};
} // namespace Presonus
