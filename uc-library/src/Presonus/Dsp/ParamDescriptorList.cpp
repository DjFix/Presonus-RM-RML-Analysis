#include "presonus/mixer_dsp/ParamDescriptorList.hpp"
#include <cstring>
#include <memory>
namespace {
std::uint32_t word(float value) {
  std::uint32_t result;
  std::memcpy(&result, &value, sizeof result);
  return result;
}
void text(presonus::dsp::DescriptorSourceState &state, const char *a,
          const char *b, const char *c) {
  state.text0.init(a ? a : "");
  state.text1.init(b ? b : "");
  state.text2.init(c ? c : "");
}
} // namespace
namespace Presonus::Dsp {
ParamDescriptor::ParamDescriptor(presonus::dsp::DescriptorSourceTag) {}
ParamDescriptor::~ParamDescriptor() {
  if ((state_.flags & 0x10000u) != 0 && state_.formatter)
    delete state_.formatter;
  if (state_.interpolator)
    delete state_.interpolator;
}
ParamDescriptorList::ParamDescriptorList(presonus::dsp::DescriptorSourceTag) {}
ParamDescriptorList::~ParamDescriptorList() {
  for (int i = 0; i < descriptors_.count(); ++i)
    delete descriptors_.at(i);
  descriptors_.resize(0);
}
ParamDescriptor *ParamDescriptorList::addFloat(
    int tag, const char *a, const char *b, const char *c, float minimum,
    float maximum, float defaultValue, const char *formatter,
    const char *interpolator, float middle, int flags) {
  const auto *found = Core::FormatterRegistry::find(formatter);
  std::unique_ptr<Core::Interpolator> curve(
      Core::InterpolatorFactory::create(interpolator));
  if (!curve)
    curve.reset(new Core::LinearInterpolator(0.f, 1.f));
  curve->setRange(minimum, maximum, middle);
  auto descriptor =
      std::make_unique<ParamDescriptor>(presonus::dsp::DescriptorSourceTag{});
  auto &state = descriptor->sourceState();
  state.tag = tag;
  state.flags = static_cast<std::uint32_t>(flags) | 0x20u;
  state.word10 = 0;
  state.word14 = word(defaultValue);
  text(state, a, b, c);
  state.formatter = found;
  state.interpolator = curve.release();
  auto *result = descriptor.release();
  descriptors_.add(result);
  return result;
}
ParamDescriptor *ParamDescriptorList::addToggle(int tag, const char *a,
                                                const char *b, const char *c,
                                                float defaultValue,
                                                const char *formatter,
                                                int flags) {
  const auto *found = Core::FormatterRegistry::find(formatter);
  auto descriptor =
      std::make_unique<ParamDescriptor>(presonus::dsp::DescriptorSourceTag{});
  auto &state = descriptor->sourceState();
  state.tag = tag;
  state.flags = static_cast<std::uint32_t>(flags) | 0x20u;
  state.word10 = 2;
  state.word14 = word(defaultValue);
  text(state, a, b, c);
  state.formatter = found;
  auto *result = descriptor.release();
  descriptors_.add(result);
  return result;
}
ParamDescriptor *ParamDescriptorList::addList(int tag, const char *a,
                                              const char *b, const char *c,
                                              const char **strings, int count,
                                              float defaultValue, int flags) {
  auto formatter =
      std::make_unique<Core::StringListFormatter>("", strings, count);
  auto curve = std::make_unique<Core::LinearInterpolator>(
      0.f, static_cast<float>(count) - 1.f);
  auto descriptor =
      std::make_unique<ParamDescriptor>(presonus::dsp::DescriptorSourceTag{});
  auto &state = descriptor->sourceState();
  state.tag = tag;
  state.flags = static_cast<std::uint32_t>(flags) | 0x10024u;
  state.word10 = static_cast<std::uint32_t>(count);
  state.word14 = word(defaultValue);
  text(state, a, b, c);
  state.formatter = formatter.release();
  state.interpolator = curve.release();
  auto *result = descriptor.release();
  descriptors_.add(result);
  return result;
}
const ParamDescriptor *ParamDescriptorList::getAt(int index) const {
  auto *descriptor = descriptors_.at(index);
  return descriptor ? descriptor : getError();
}
ParamDescriptor *ParamDescriptorList::getError() {
  static ParamDescriptor error(presonus::dsp::DescriptorSourceTag{});
  return &error;
}
} // namespace Presonus::Dsp
