#pragma once

#include "presonus/IFaderUnit.hpp"
#include "presonus/MackieControlModel.hpp"

namespace Presonus::Surface {
// Source-port bridge for the verified Mackie model path. The existing portable
// IFaderUnit exposes no sink-binding virtual and MackieControlModel has no
// base.
class MackieFaderUnitBinding final : public IFaderUnit {
public:
  explicit MackieFaderUnitBinding(MackieControlModel &model)
      : IFaderUnit(SourcePortTag{}), model_(model) {}
  void setMidiSink(IMidiSink *sink) { model_.setMidiSink(sink, 0); }

private:
  MackieControlModel &model_;
};

// This subset preserves local sink binding; sending through a UC connection
// belongs to a separate method. The caller supplies the portable send endpoint.
class UCMidiOutputAdapter : public IMidiSink {
public:
  UCMidiOutputAdapter();
  explicit UCMidiOutputAdapter(IMidiSink &endpoint) : endpoint_(&endpoint) {}
  virtual ~UCMidiOutputAdapter();

  UCMidiOutputAdapter(const UCMidiOutputAdapter &) = delete;
  UCMidiOutputAdapter &operator=(const UCMidiOutputAdapter &) = delete;

  void setFaderUnit(IFaderUnit *, int);
  void sendMidiMessage(const unsigned char *, unsigned int,
                       unsigned int) override;
  IMidiSink *portableEndpoint() const { return endpoint_; }
  IFaderUnit *portableFaderUnit() const { return fader_; }

private:
  IMidiSink *endpoint_{};
  MackieFaderUnitBinding *fader_{};
};
} // namespace Presonus::Surface
