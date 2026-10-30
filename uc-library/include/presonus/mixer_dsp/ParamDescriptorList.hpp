#pragma once
#include "core/public/coreformatter.h"
#include "core/public/coreinterpolator.h"
#include "core/public/corestringbuffer.h"
#include "core/public/corevector.h"
#include <cstdint>
namespace presonus::dsp {
// Independent construction/state access, not recovered original constructors,
// field declarations, class inheritance or ARM object layout.
struct DescriptorSourceTag {};
struct DescriptorSourceState {
  int tag = 0;
  std::uint32_t flags = 32, word10 = 0, word14 = 0, word18 = 32;
  Core::CStringBuffer<32> text0, text1, text2;
  const Core::Formatter *formatter = nullptr;
  Core::Interpolator *interpolator = nullptr;
};
} // namespace presonus::dsp
namespace Presonus::Dsp {
class ParamDescriptor {
public:
  explicit ParamDescriptor(presonus::dsp::DescriptorSourceTag);
  ~ParamDescriptor();
  ParamDescriptor(const ParamDescriptor &) = delete;
  ParamDescriptor &operator=(const ParamDescriptor &) = delete;
  presonus::dsp::DescriptorSourceState &sourceState() { return state_; }
  const presonus::dsp::DescriptorSourceState &sourceState() const {
    return state_;
  }

private:
  presonus::dsp::DescriptorSourceState state_;
};
class ParamDescriptorList {
public:
  explicit ParamDescriptorList(presonus::dsp::DescriptorSourceTag);
  ~ParamDescriptorList();
  ParamDescriptorList(const ParamDescriptorList &) = delete;
  ParamDescriptorList &operator=(const ParamDescriptorList &) = delete;
  // Pointer return/const qualification/static membership are portable choices;
  // these five original ordinary declarations remain pending.
  ParamDescriptor *addFloat(int, const char *, const char *, const char *,
                            float, float, float, const char *, const char *,
                            float, int);
  ParamDescriptor *addToggle(int, const char *, const char *, const char *,
                             float, const char *, int);
  ParamDescriptor *addList(int, const char *, const char *, const char *,
                           const char **, int, float, int);
  const ParamDescriptor *getAt(int) const;
  static ParamDescriptor *getError();
  int sourceCount() const { return descriptors_.count(); }

private:
  // Real CCL composition is an explicit source-port decision. No original
  // vector inheritance/member layout is asserted.
  Core::Vector<ParamDescriptor *> descriptors_;
};
} // namespace Presonus::Dsp
