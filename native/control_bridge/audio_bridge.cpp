#include "AudioNetwork.h"
#include "public.sdk/source/vst/vstsinglecomponenteffect.h"
#include "public.sdk/source/main/pluginfactory.h"
#include "pluginterfaces/vst/ivstparameterchanges.h"
#include "base/source/fstreamer.h"
using namespace Steinberg;
using namespace Steinberg::Vst;
static const FUID audioUID(0xB1D97C52, 0x07CA49DF, 0xA1D960F5, 0x7280CB11);

class AudioBridgeEffect final : public SingleComponentEffect {
    AudioNetwork network;
    std::atomic<bool> wet {true};
public:
    static FUnknown* create(void*) { return static_cast<IAudioProcessor*>(new AudioBridgeEffect); }
    tresult PLUGIN_API initialize(FUnknown* context) override {
        auto result = SingleComponentEffect::initialize(context);
        if (result != kResultOk) return result;
        addAudioInput(STR16("DAW Input"), SpeakerArr::kStereo);
        addAudioOutput(STR16("TouchMusic Return"), SpeakerArr::kStereo);
        parameters.addParameter(STR16("Wet return"), nullptr, 1, 1, ParameterInfo::kCanAutomate, 0);
        return kResultOk;
    }
    uint32 PLUGIN_API getLatencySamples() override { return AudioNetwork::delay; }
    tresult PLUGIN_API setActive(TBool state) override {
        if (state) network.start(); else network.stop();
        return SingleComponentEffect::setActive(state);
    }
    tresult PLUGIN_API terminate() override { network.stop(); return SingleComponentEffect::terminate(); }
    tresult PLUGIN_API setParamNormalized(ParamID id, ParamValue value) override {
        if (id != 0 || !std::isfinite(value)) return kInvalidArgument;
        wet.store(value >= .5);
        return SingleComponentEffect::setParamNormalized(id, value);
    }
    tresult PLUGIN_API canProcessSampleSize(int32 size) override {
        return size == kSample32 || size == kSample64 ? kResultTrue : kResultFalse;
    }
    tresult PLUGIN_API setBusArrangements(SpeakerArrangement* in, int32 ins,
                                         SpeakerArrangement* out, int32 outs) override {
        if (ins != 1 || outs != 1 || in[0] != out[0]
            || (in[0] != SpeakerArr::kMono && in[0] != SpeakerArr::kStereo)) return kResultFalse;
        return SingleComponentEffect::setBusArrangements(in, ins, out, outs);
    }
    tresult PLUGIN_API process(ProcessData& data) override {
        if (data.inputParameterChanges && data.inputParameterChanges->getParameterCount()) {
            auto* changes = data.inputParameterChanges->getParameterData(0);
            int32 offset; ParamValue value;
            if (changes && changes->getParameterId() == 0 && changes->getPointCount()
                && changes->getPoint(changes->getPointCount()-1, offset, value) == kResultTrue) wet.store(value >= .5);
        }
        if (!data.numOutputs || !data.numSamples) return kResultOk;
        network.collect();
        auto& output = data.outputs[0]; output.silenceFlags = 0;
        for (int32 frame = 0; frame < data.numSamples; ++frame) {
            float left = 0, right = 0, outLeft, outRight;
            if (data.numInputs && data.inputs[0].numChannels) {
                auto& input = data.inputs[0];
                left = data.symbolicSampleSize == kSample64 ? static_cast<float>(input.channelBuffers64[0][frame])
                                                           : input.channelBuffers32[0][frame];
                auto channel = std::min<int32>(1, input.numChannels-1);
                right = data.symbolicSampleSize == kSample64 ? static_cast<float>(input.channelBuffers64[channel][frame])
                                                            : input.channelBuffers32[channel][frame];
            }
            network.sample(left, right, outLeft, outRight, processSetup.sampleRate, wet.load());
            for (int32 channel = 0; channel < output.numChannels; ++channel) {
                float value = channel == 0 ? outLeft : outRight;
                if (data.symbolicSampleSize == kSample64) output.channelBuffers64[channel][frame] = value;
                else output.channelBuffers32[channel][frame] = value;
            }
        }
        return kResultOk;
    }
    tresult PLUGIN_API getState(IBStream* stream) override {
        if (!stream) return kInvalidArgument;
        IBStreamer writer(stream, kLittleEndian);
        return writer.writeDouble(wet.load() ? 1. : 0.) ? kResultOk : kResultFalse;
    }
    tresult PLUGIN_API setState(IBStream* stream) override {
        if (!stream) return kInvalidArgument;
        IBStreamer reader(stream, kLittleEndian); double value;
        return reader.readDouble(value) ? setParamNormalized(0, value) : kResultFalse;
    }
};
BEGIN_FACTORY_DEF("TouchMusic", "https://github.com/RealShocky/TouchMusic", "")
DEF_CLASS2(INLINE_UID_FROM_FUID(audioUID), PClassInfo::kManyInstances, kVstAudioEffectClass,
           "TouchMusic Audio Bridge", 0, "Fx|Tools", "0.5.0", kVstVersionString, AudioBridgeEffect::create)
END_FACTORY
