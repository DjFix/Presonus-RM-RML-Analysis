#include "presonus/mixer/PreDelayFormatterT7.hpp"
namespace Presonus::Mixer {
PreDelayFormatterT7::~PreDelayFormatterT7() = default;
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT7>() {
  static PreDelayFormatterT7 theFormatter(PreDelayFormatterT7::SourcePortTag{});
  Core::FormatterRegistry::add(&theFormatter);
}
} // namespace Presonus::Mixer
