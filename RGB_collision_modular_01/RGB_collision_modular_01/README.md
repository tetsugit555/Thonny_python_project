# RGB_data_collision_08 モジュール版

元の `RGB_data_collision_08.py` の処理順、UI、初期値、フレーム生成、合成方式を維持し、ファイル単位に分割したものです。

## 起動

すべての `.py` ファイルを同じフォルダに置き、`python main.py` で起動。依存ライブラリは `pip install -r requirements.txt`。Instagram変換には外部 `ffmpeg` が必要です。

## モジュール仕様

| ファイル | 入力 | 出力・副作用 |
|---|---|---|
| `bmp_analyzer.py` | `analyze_bmp(path: str)` BMPパス | `BMPAnalysis`：`rgb` (H,W,3) uint8、`width`、`height`、`row_colors` (H,3)、`col_colors` (W,3)。RGB順 |
| `stripe_generator.py` | `create_stripes(data: BMPAnalysis)` | `(horizontal_rgb, vertical_rgb)` 各 (H,W,3) uint8、RGB順 |
| `grid_generator.py` | `blend_lighten(horizontal, vertical)` | `np.maximum` のRGB画像 (H,W,3) uint8。動画内の縦走査では到達範囲だけに逐次適用 |
| `grid_generator.py` | `difference_grid(horizontal, vertical)` | `abs(horizontal - vertical)` のRGB画像 (H,W,3) uint8 |
| `stripe_motion.py` | `make_motion(count,duration,rng)` | `(starts,travel)` 配列。`get_positions(t,starts,travel,length)` → 進捗位置配列 |
| `text_renderer.py` | `rgb_text(color)`、`draw_text(frame,text,x,y,...)`、`draw_glyphs(frame,glyphs)` など | RGB文字列、BGRフレームの**直接変更**。クラスの表示設定を参照 |
| `rgb_stream.py` | `make_stream(width,height,rng,palette,...)` | ストリーム辞書。`advance_streams(streams,dt,...)` はリストを更新。`stream_glyphs(...)` → 文字辞書リスト |
| `rgb_collision.py` | `make_collision(x,y,now,a_color,b_color,d_color,width,height,rng)` | 衝突イベント辞書。`collision_glyphs(event,now,width)` → 描画文字辞書リスト |
| `video_renderer.py` | `create_video()`：GUIのパス・設定値・保存ダイアログ | MP4を保存、ステータスを更新。内部でBMP解析→ストライプ→走査→グリッド→文字演出→出力 |
| `video_export.py` | `convert_instagram(source,destination)`：MP4パス | FFmpegで1080×1920 H.264 MP4保存。失敗時は例外 |
| `main.py` | Tkルート、GUI操作 | アプリを起動し、各Mixinを組み合わせる |

### 重要な仕様・互換性

- **内部画像の色順**：解析とストライプ／グリッド演算はRGB。OpenCV描画・VideoWriterはBGR。`video_renderer.py` で変換。
- **比較（明）**：縦ストライプの走査中、既存の横ストライプとRGB各成分の最大値で重ねる。
- **グリッド**：完成形はRGB差の絶対値。横・縦走査の交差済み領域を順次この画像へ置き換える。
- **RGB衝突**：横平均色・縦平均色・差の絶対値を文字にし、左右から衝突する演出。グリッド完成後も新規イベントを生成。
- **時間・フレーム**：30fps。元版の計算式を維持。ランダム演出は毎回変わる。
- **構造**：描画・ストリーム・衝突・動画は、動作の互換性を優先して `Mixin` クラスに分離。`self` の状態を使うため、**完全独立の関数型APIではない**。画像解析・ストライプ生成・合成計算の3モジュールは親アプリなしで直接利用可能。
- `blend_lighten` は単独利用向けの純粋関数で、元版の走査演出そのものは `video_renderer.py` 内の `scan(..., lighten=True)` が担当する。

## 画像解析モジュール単独利用例

```python
from bmp_analyzer import analyze_bmp
from stripe_generator import create_stripes
from grid_generator import blend_lighten, difference_grid

data = analyze_bmp("sample.bmp")
h, v = create_stripes(data)
lighten = blend_lighten(h, v)
grid = difference_grid(h, v)
print(data.width, data.height, grid.shape)
```

## EXE化

Windowsで、フォルダ内から例：

```powershell
python -m PyInstaller --onefile --windowed --name RGB_collision_modular main.py
```

FFmpegは従来同様、別途PATHに登録が必要です。
