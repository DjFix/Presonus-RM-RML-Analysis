#pragma once

namespace Presonus::Mixer {

class FxTypeFormatter;
class PreDelayFormatterT9;
class FxReverbNumFormatter;

class XmenFormatterInitializer {
public:
  template <class Formatter> static void addClass();
};

template <> void XmenFormatterInitializer::addClass<FxTypeFormatter>();
template <> void XmenFormatterInitializer::addClass<PreDelayFormatterT9>();
template <> void XmenFormatterInitializer::addClass<FxReverbNumFormatter>();

} // namespace Presonus::Mixer
