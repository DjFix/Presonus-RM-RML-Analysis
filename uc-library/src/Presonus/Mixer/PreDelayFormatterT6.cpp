#include "presonus/mixer/PreDelayFormatterT6.hpp"
namespace Presonus::Mixer {
PreDelayFormatterT6::~PreDelayFormatterT6() = default;
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT6>() {
  static PreDelayFormatterT6 theFormatter(PreDelayFormatterT6::SourcePortTag{});
  Core::FormatterRegistry::add(&theFormatter);
}
} // namespace Presonus::Mixer
