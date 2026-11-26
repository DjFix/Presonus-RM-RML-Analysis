#include "presonus/mixer/PreDelayFormatterT9.hpp"
#include "presonus/mixer/XmenFormatterInitializer.hpp"
namespace Presonus::Mixer {
PreDelayFormatterT9::~PreDelayFormatterT9() = default;
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT9>() {
  static PreDelayFormatterT9 theFormatter(PreDelayFormatterT9::SourcePortTag{});
  Core::FormatterRegistry::add(&theFormatter);
}

} // namespace Presonus::Mixer
