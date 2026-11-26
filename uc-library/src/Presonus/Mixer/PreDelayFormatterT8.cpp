#include "presonus/mixer/PreDelayFormatterT8.hpp"
namespace Presonus::Mixer {
PreDelayFormatterT8::~PreDelayFormatterT8() = default;
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT8>() {
  static PreDelayFormatterT8 theFormatter(PreDelayFormatterT8::SourcePortTag{});
  Core::FormatterRegistry::add(&theFormatter);
}
} // namespace Presonus::Mixer
