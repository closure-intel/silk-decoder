/*
 * _silk — thin CPython wrapper around the vendored Skype SILK SDK decoder.
 *
 * This is the only hand-written C in the package. It does NOT implement any codec
 * DSP; it drives the vendored reference decoder (vendor/silk/) the same way the SDK's
 * own test/Decoder.c does: init a decoder, then for each SILK frame call
 * SKP_Silk_SDK_Decode in a loop until moreInternalDecoderFrames clears, accumulating
 * signed-16-bit PCM. Container framing (the 0x02 prefix, #!SILK_V3 magic, and the
 * length-prefixed frames) is parsed in Python (container.py) and the raw frame
 * payloads are passed in here — so framing lives in one place and this stays minimal.
 *
 * Output is native-endian int16; every platform we target (x86_64 / arm64, macOS +
 * Linux) is little-endian, so it is already s16le for the WAV writer.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>

#include "SKP_Silk_SDK_API.h"
#include "SKP_Silk_control.h"

/* One SKP_Silk_SDK_Decode call emits at most one internal 20 ms frame. 2048 samples
 * is comfortably above 20 ms at any SILK API rate (8/12/16/24 kHz -> <=480). */
#define SILK_SAMPLES_PER_CALL 2048

static PyObject *SilkNativeError;

static PyObject *decode_frames(PyObject *self, PyObject *args) {
    PyObject *frames_obj;
    int sample_rate;
    if (!PyArg_ParseTuple(args, "Oi", &frames_obj, &sample_rate)) {
        return NULL;
    }

    PyObject *frames = PySequence_Fast(frames_obj, "frames must be a sequence of bytes");
    if (!frames) {
        return NULL;
    }
    Py_ssize_t n_frames = PySequence_Fast_GET_SIZE(frames);

    SKP_int32 dec_size = 0;
    if (SKP_Silk_SDK_Get_Decoder_Size(&dec_size)) {
        Py_DECREF(frames);
        PyErr_SetString(SilkNativeError, "SKP_Silk_SDK_Get_Decoder_Size failed");
        return NULL;
    }
    void *dec_state = PyMem_Malloc(dec_size);
    if (!dec_state) {
        Py_DECREF(frames);
        return PyErr_NoMemory();
    }
    if (SKP_Silk_SDK_InitDecoder(dec_state)) {
        PyMem_Free(dec_state);
        Py_DECREF(frames);
        PyErr_SetString(SilkNativeError, "SKP_Silk_SDK_InitDecoder failed");
        return NULL;
    }

    SKP_SILK_SDK_DecControlStruct dec_control;
    memset(&dec_control, 0, sizeof(dec_control));
    dec_control.API_sampleRate = sample_rate;

    SKP_int16 *pcm = NULL;
    size_t pcm_samples = 0, pcm_cap = 0;
    SKP_int16 frame_out[SILK_SAMPLES_PER_CALL];

    for (Py_ssize_t i = 0; i < n_frames; i++) {
        PyObject *item = PySequence_Fast_GET_ITEM(frames, i); /* borrowed */
        char *payload;
        Py_ssize_t payload_len;
        if (PyBytes_AsStringAndSize(item, &payload, &payload_len) < 0) {
            goto error; /* not a bytes object */
        }

        SKP_int16 more = 0;
        do {
            SKP_int16 n_samples = SILK_SAMPLES_PER_CALL;
            int ret = SKP_Silk_SDK_Decode(dec_state, &dec_control, 0,
                                          (const SKP_uint8 *)payload, (SKP_int16)payload_len,
                                          frame_out, &n_samples);
            if (ret) {
                PyErr_Format(SilkNativeError, "SKP_Silk_SDK_Decode returned %d", ret);
                goto error;
            }
            if (pcm_samples + (size_t)n_samples > pcm_cap) {
                size_t new_cap = pcm_cap ? pcm_cap * 2 : 48000;
                while (new_cap < pcm_samples + (size_t)n_samples) {
                    new_cap *= 2;
                }
                SKP_int16 *grown = (SKP_int16 *)realloc(pcm, new_cap * sizeof(SKP_int16));
                if (!grown) {
                    PyErr_NoMemory();
                    goto error;
                }
                pcm = grown;
                pcm_cap = new_cap;
            }
            memcpy(pcm + pcm_samples, frame_out, (size_t)n_samples * sizeof(SKP_int16));
            pcm_samples += (size_t)n_samples;
            more = dec_control.moreInternalDecoderFrames;
        } while (more);
    }

    PyObject *result = PyBytes_FromStringAndSize((const char *)pcm, (Py_ssize_t)(pcm_samples * sizeof(SKP_int16)));
    free(pcm);
    PyMem_Free(dec_state);
    Py_DECREF(frames);
    return result;

error:
    free(pcm);
    PyMem_Free(dec_state);
    Py_DECREF(frames);
    return NULL;
}

static PyMethodDef silk_methods[] = {
    {"decode_frames", decode_frames, METH_VARARGS,
     "decode_frames(frames: Sequence[bytes], sample_rate: int) -> bytes\n\n"
     "Decode SILK v3 frame payloads to signed-16-bit little-endian mono PCM."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef silk_module = {
    PyModuleDef_HEAD_INIT,
    "silk_decoder._silk",
    "Native SILK v3 decode via the vendored Skype SILK SDK.",
    -1,
    silk_methods,
    NULL, NULL, NULL, NULL,
};

PyMODINIT_FUNC PyInit__silk(void) {
    PyObject *module = PyModule_Create(&silk_module);
    if (!module) {
        return NULL;
    }
    SilkNativeError = PyErr_NewException("silk_decoder._silk.SilkNativeError", NULL, NULL);
    Py_XINCREF(SilkNativeError);
    if (PyModule_AddObject(module, "SilkNativeError", SilkNativeError) < 0) {
        Py_XDECREF(SilkNativeError);
        Py_DECREF(module);
        return NULL;
    }
    return module;
}
