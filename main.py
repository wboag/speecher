import dash
from dash import html, dcc, Input, Output, State, ALL, MATCH
from flask import Flask, send_from_directory

import os
import pickle
import json
import base64
import math
import copy
from pdf2image import convert_from_path
from io import StringIO
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from bs4 import BeautifulSoup
import re
from collections import defaultdict

from source.tts import text_to_mp3



# File paths
PROJECT_DIR = '/Users/wboag/Desktop/webapps/speecher'

# Where to store annotations
anns_dir = img_file = os.path.join(PROJECT_DIR, 'static/ml')


# Where to store PDFs uploaded to the server
UPLOAD_DIRECTORY = "/Users/wboag/Desktop/webapps/speecher/static/assets"
if not os.path.exists(UPLOAD_DIRECTORY):
    os.makedirs(UPLOAD_DIRECTORY)



#####################################
##      Metadata and Files         ##
#####################################


def save_file(name, content):
    """Decode and store a file uploaded with Plotly Dash."""
    data = content.encode("utf8").split(b";base64,")[1]
    filename = os.path.join(UPLOAD_DIRECTORY, name)
    print(f'saving to {filename}')
    with open(filename, "wb") as fp:
        fp.write(base64.decodebytes(data))
        

        
def build_annotation_filename(annotation_name):
    cleaned_name = annotation_name.replace('.', '_')
    return os.path.join(anns_dir, f'{cleaned_name}.json')



#####################################
##            Helpers              ##
#####################################


def find_top(vals, top):
    for i in range(len(vals)):
        if top <= vals[i]:
            return vals[i-1]
    return vals[-1]
        
def find_page(vals, top):
    for i in range(len(vals)):
        if top <= vals[i]:
            return i-1
    return len(vals)-1
        


def save_local_annotations(children, annotation_name, pdf_info_s):
    pdf_info = json.loads(pdf_info_s)
    annotations = pdf_info['annotations']
    
    # Amend annotations based on current boxes
    for pg_node in children[1:]:
        pg = pg_node['props']['children'][0]['props']['children']
        for element in pg:
            props = element['props']
            if ('id' in props) and (re.search('span-\d+-\d+',props['id']['index'])):
                current_background = props['style']['background-color']
                opacity = float(re.search('rgba\(\d+,\d+,\d+,(\d?\.?\d+)\)', current_background).groups()[0])
                #print(props['id']['index'], opacity)
                annotations[props['id']['index']] = int(opacity>0)
    
    # pickle this info to disk (to be read on next load)
    anns_file = build_annotation_filename(annotation_name)
    with open(anns_file, 'wb') as f:
        pickle.dump(annotations, f)



#####################################
##      Processing Data            ##
#####################################


# Here the PDF is converted to list of images
def pdf_to_images(pdf_file):
    page_images = convert_from_path(pdf_file,size=(1020,1320))

    pdfname = pdf_file.split('/')[-1]
    pdfname = pdfname.replace('.', '_')

    # Save Images (tempoarily) for visualization
    img_dir = '.'
    img_dir = f'static/assets/images/{pdfname}'
    if not os.path.exists(img_dir):
        print(f'Making tmp image assets dir: {img_dir}')
        os.mkdir(img_dir)

        # Save images to temp dir
        for pageno in range(len(page_images)):
            img_file = os.path.join(img_dir, f'{pageno}.jpg')
            with open(img_file, 'w') as f:
                page_images[pageno].save(f)
            
    return img_dir, page_images



# Convert PDF into html formatted document
def extract_textboxes(pdf_file):
    # turn PDF into html-format
    output_string = StringIO()
    with open(pdf_file, 'rb') as fin:
        extract_text_to_fp(fin, output_string, laparams=LAParams(),
                           output_type='html', codec=None)
    html_text = output_string.getvalue()

    # Parse HTML
    soup = BeautifulSoup(html_text)
    
    ### Extract the coordinates of each text box
    # Extract where each PDF page begins in HTML pixel-space
    unordered_tops = re.findall('<span style="position:absolute;.*?top:(\d+)px; width:612px; height:792px.*?>',
                                html_text)
    page_tops = sorted(set(map(int,unordered_tops)))
    textboxes = defaultdict(list)
    for i,div in enumerate(soup.findAll('div')):
        if 'textbox' in div.attrs['style']:
            if 'textbox' in div.attrs['style']:
                left   = int(re.search(  'left:(\d+)px', div.attrs['style']).groups()[0])
                top    = int(re.search(   'top:(\d+)px', div.attrs['style']).groups()[0])
                width  = int(re.search( 'width:(\d+)px', div.attrs['style']).groups()[0])
                height = int(re.search('height:(\d+)px', div.attrs['style']).groups()[0])
                text = div.text
                textbox = {'left':left, 'top':top, 'width':width, 'height':height, 'text':text}
                pageno = find_page(page_tops, top)
                
                textboxes[pageno].append(textbox)
    return textboxes, page_tops



#@app.callback(
#    Output("tabs-example-graph", "children"),
#    [
#     Input('dropdown-pages', 'value'),
#     State("tabs-example-graph", "children"), 
#     State('pdf_info','data')
#    ],
#    prevent_initial_call=True
#)
def update_page_tabs(value, tabs, pdf_info_s):
    if value is None: return tabs, pdf_info_s
    
    # Load the textboxes
    pdf_info = json.loads(pdf_info_s)
    annotations = pdf_info['annotations']
    img_dir = pdf_info['img_dir']
    page_tops = pdf_info['page_tops']
    textboxes = {int(pageno):textbox for pageno,textbox in pdf_info['textboxes'].items()}
        
    # Amend annotations based on current boxes
    # Batching this here because would be too costly to update (and pass big args) for each button toggle
    for pg_node in tabs[1:]:
        pg = pg_node['props']['children'][0]['props']['children']
        for element in pg:
            props = element['props']
            if ('id' in props) and (re.search('span-\d+-\d+',props['id']['index'])):
                current_background = props['style']['background-color']
                opacity = float(re.search('rgba\(\d+,\d+,\d+,(\d?\.?\d+)\)', current_background).groups()[0])
                #print(props['id']['index'], opacity)
                annotations[props['id']['index']] = int(opacity>0)
    pdf_info['annotations'] = annotations
    new_pdf_info_s = json.dumps(pdf_info)
        
    # Which range of pages (based on the dropdown selection)
    matches = re.search('Pages\s+(\d+)-\s*(\d+)', value).groups()
    low  = int(matches[0])-1
    high = int(matches[1])
    
    # Create a tab for each PDF page in the pagenos range
    pagenos = range(low, high)
    pdf_page_tabs = create_pdf_page_tabs(textboxes, img_dir, pagenos, page_tops, annotations)
    new_tabs = [tabs[0]] + pdf_page_tabs
    
    return new_tabs, new_pdf_info_s



#@app.callback(
#    [
#     Output('pdf_info','data'),
#     Output('div-filename', 'children'),
#     Output('dropdown-pages-holder', 'children'),
#    ],
#    [Input("upload-data", "filename"), Input("upload-data", "contents"), 
#     State('pdf_info','data'),
#     State('div-filename', 'children'),
#     State('dropdown-pages-holder', 'children'),
#     State('dropdown-pages', 'value'),
#    ],
#)
def load_uploaded_pdf(uploaded_filename, uploaded_file_content, old_pdf_info_s, current_pdf_name, dropdown, dvalue):
    """Save uploaded files and regenerate the file list."""
    
    ### Error Checking & administrivia

    # This *shouldnt* run unless a new pdf was uploaded. Reloading Tabs.children (to switch pdf pages) doesnt count
    # If there is an "update" (aka new Tabs.children) but no real change, then skip.
    if len(old_pdf_info_s):
        pdf_info = json.loads(old_pdf_info_s)
        annotation_name = pdf_info['annotation_name']
        if uploaded_filename == annotation_name: return old_pdf_info_s, current_pdf_name, dropdown
    
    # Assert must be a PDF
    if not uploaded_filename.endswith('.pdf'):
        # TODO:have some kind of "mus upload .pdf" error message
        return old_pdf_info_s, current_pdf_name, dropdown
    
    ### Load and Process PDF
    # Save uploaded pdf to server
    save_file(uploaded_filename, uploaded_file_content)
    
    # Which PDF is loaded
    pdf_file = f'static/assets/{uploaded_filename}'
    annotation_name = uploaded_filename
    
    # Process pdf
    textboxes, page_tops = extract_textboxes(pdf_file)
    w3,w4 = textboxes, page_tops
    
    # Create images of each page of PDF
    img_dir, page_images = pdf_to_images(pdf_file)
    w1, w2 = img_dir, page_images

    # load annotations from cache
    anns_file = build_annotation_filename(annotation_name)
    if os.path.exists(anns_file):
        with open(anns_file, 'rb') as f:
            annotations = pickle.load(f)
    else:
        # TODO: could do ML here to have better guesses
        # initialize all annotations (we know 1:1 match of textbox-to-annotation) to on
        annotations = {}
        for pageno in range(len(textboxes)):
            pg_tbs = textboxes[pageno]
            for j in range(len(pg_tbs)):
                aid = f'span-{pageno}-{j}'
                annotations[aid] = 0.3
        
    # store metadata in the dcc.Store() variable
    pdf_info = {'annotation_name':annotation_name, 'textboxes':dict(textboxes), 
                'img_dir':img_dir, 'page_tops':page_tops, 'annotations':annotations}
    pdf_info_s = json.dumps(pdf_info)
    
    # Update description of which file is loaded
    new_filename_text = dcc.Markdown(f'Uploaded: **{uploaded_filename}**')
        
    # Update the dropdown to reflect page segments (note: must take new_dropdown to trigger late callback)
    batchsize = 8 # the dropdown is hard-coded to fit 8 tabs (plus the app cant handle much more than that)
    options = []
    for i in range(math.ceil(len(w2) / 8)):
        upper = min(len(w2), 8*(i+1))
        title = f'Pages {8*i+1:2d}-{upper:2d}'
        options.append(title)
    new_dropdown = copy.copy(dropdown)
    new_dropdown[0]['props']['options']  = options
    new_dropdown[0]['props']['value']    = options[0]
    new_dropdown[0]['props']['disabled'] = False
    new_dropdown[0]['props']['clearable'] = False
    w5 = new_dropdown
        
    return pdf_info_s, new_filename_text, new_dropdown



def create_pdf_page_tabs(textboxes, img_dir, pagenos, page_tops, annotations):    
    pdf_page_tabs = []
    for pageno in pagenos:
        # Find top of page (to get the pixel height offset correct)
        if len(textboxes[pageno]):
            page_top = find_top(page_tops, textboxes[pageno][0]['top'])

        # Format the list of textboxes to highlight for this PDF page
        boxes = []
        for i,textbox in enumerate(textboxes[pageno]):
            left = textbox['left']
            top = (textbox['top']-page_top)
            width = textbox['width']
            height = textbox['height']

            button_key = f'span-{pageno}-{i}'
            button_id = {'type':'button', 'index':button_key}
            
            # If in annotations page, determine if the box should start on or off
            if button_key in annotations:
                if annotations[button_key] == 0:
                    opacity = 0
                else:
                    opacity = 0.3
            else:
                opacity = 0.3

            span = html.Button(id=button_id,
                               n_clicks=0,
                               style={'position':'absolute','left':f'{left+tabwidth}px', 'top':f'{top+boxsize}px',
                                      'width':f'{width}px','height':f'{height}px', 
                                      'border':'gray 1px solid',
                                      'background-color':f'rgba(255,255,0,{opacity})'})
            boxes.append(span)

        # What layout goes into this tab?
        img_file = os.path.join(img_dir, f'{pageno}.jpg')
        tab_layout = html.Div(id=f'layout-{pageno}',
            children=[html.Div('Un-highlight which boxes to exclude.',
                               style={'position':'absolute',
                                      'top':'0px', 'left':f'{tabwidth}px',
                                      'width':'612px', 'height':f'20px',
                                      'border':'gray 1px solid'}),
                      html.Img(src=img_file,  style={'position':'absolute', 'border':'gray 1px solid',
                                                   'left':f'{tabwidth}px', 'top':f'{boxsize}px',
                                                   'width':'612px', 'height':'792px'}), # pixel space of PDFs
                      ]+boxes)

        # Add this entry to the list of tabs
        tab = dcc.Tab(label=f'Page {pageno+1}', value=f'tab-{pageno}-example-graph', children=[tab_layout])
        pdf_page_tabs.append(tab)

    return pdf_page_tabs



#####################################
##           Setup App             ##
#####################################


# Normally, Dash creates its own Flask server internally. 
# By creating our own, we can create a route for downloading files directly:
server = Flask(__name__)
app = dash.Dash(server=server)
#app.config['suppress_callback_exceptions']=False


@server.route("/download/<path:path>")
def download(path):
    """Serve a file from the upload directory."""
    return send_from_directory(UPLOAD_DIRECTORY, path, as_attachment=True)



# pdf_info updated by uploading new PDF _or_ saving annotations 
@app.callback(
    [
     Output("tabs-example-graph", "children"),
     Output("tabs-example-graph", "value"),
     Output('pdf_info','data'),
     Output('div-filename', 'children'),
     Output('dropdown-pages-holder', 'children'),

    ],
    [Input("upload-data", "filename"), Input("upload-data", "contents"), 
     
     Input('save-ann-button', 'n_clicks'),

     Input('dropdown-pages', 'value'),

     State('pdf_info','data'),
     State('div-filename', 'children'),
     State('dropdown-pages-holder', 'children'),
     State('tabs-example-graph', 'children'),
     State('tabs-example-graph', 'value')

    ],
    prevent_initial_call=True
)
def update_pdf_info_router(uploaded_filename, uploaded_file_content,
                      s_clicks,
                      dropdown_val, 
                      old_pdf_info_s, current_pdf_name, dropdown, tabs, tabval):

    # TODO: this is ugly & clumsy, passing large 'tabs' because I need to modify annotations in 2 different places
    #       but dash only allows one callback to cover a given Output
    
    triggered_id = dash.callback_context.triggered_id
    #print('TRIGGERED:', triggered_id)
    if triggered_id is None:
        return  tabs, tabval, old_pdf_info_s, current_pdf_name, dropdown

        
    elif triggered_id == 'upload-data':
        pdf_info_s, pdfname, new_dropdown = load_uploaded_pdf(uploaded_filename, uploaded_file_content,
                                                              old_pdf_info_s, current_pdf_name,
                                                              dropdown, dropdown_val)
        
        # If we didnt have ugly mega-callback, this would been able to figure on its own after the above finished
        new_dropdown_val = new_dropdown[0]['props']['value'] 
        new_tabs, new_pdf_info_s = update_page_tabs(new_dropdown_val, tabs, pdf_info_s)
        return new_tabs, tabval, pdf_info_s, pdfname, new_dropdown
        
    elif triggered_id == 'save-ann-button':
        save_local_annotations(tabs, uploaded_filename, old_pdf_info_s)
        return tabs, tabval, old_pdf_info_s, current_pdf_name, dropdown
    
    elif triggered_id == 'dropdown-pages':
        new_tabs, new_pdf_info_s = update_page_tabs(dropdown_val, tabs, old_pdf_info_s)
        
        # Set current tab to one of the ones in the new batch
        matches = re.search('Pages\s+(\d+)-\s*(\d+)', dropdown_val).groups()
        low  = int(matches[0])-1
        new_tabval = f'tab-{low}-example-graph'
                
        return new_tabs, new_tabval, new_pdf_info_s, current_pdf_name, dropdown

    else:
        print('PANIC!!!')
        return tabs, tabval, old_pdf_info_s, current_pdf_name, dropdown




@app.callback(
    Output({'type': 'button', 'index': MATCH}, 'style'),
    [Input({'type': 'button', 'index': MATCH}, 'n_clicks'), 
     State({'type': 'button', 'index': MATCH}, 'style'),
     Input(f'unselect-button', 'n_clicks'), Input(f'select-button', 'n_clicks'),
     State('tabs-example-graph', 'value')],
    prevent_initial_call=True
)
def toggle_box(n_clicks, style, uclicks, slicks, tabs_value):
    trigger_id_d = dash.callback_context.triggered_id # {'index': 'span-8-2', 'type': 'button'}
    
    # Do nothing on initialization call
    if trigger_id_d is None:
        return style
    
    # Determine which button was clicked
    if str(type(trigger_id_d)) == "<class 'dash._utils.AttributeDict'>":
        trigger_id = trigger_id_d['index']
    else:
        trigger_id = trigger_id_d

    if trigger_id.startswith('span'):
        # Toggle opacity
        current_background = style['background-color']
        opacity = float(re.search('rgba\(\d+,\d+,\d+,(\d?\.?\d+)\)', current_background).groups()[0])
        if opacity > 0:
            new_opacity = 0
        else:
            new_opacity = 0.3

        style['background-color'] = f'rgba(255,255,0,{new_opacity})'

    elif trigger_id == 'unselect-button':
        # dash.callback_context.outputs_list == {'id': {'index': 'span-9-2', 'type': 'button'}, 'property': 'style'}
        pageno = int(dash.callback_context.outputs_list['id']['index'].split('-')[1])

        # tabs_value == tab-10-example-graph
        tabno = int(tabs_value.split('-')[1])
        
        # If on the correct page, turn button off
        if pageno==tabno:    
            style['background-color'] = f'rgba(255,255,0,0)'

    elif trigger_id == 'select-button':
        # dash.callback_context.outputs_list == {'id': {'index':'span-9-2', 'type':'button'}, 'property':'style'}
        pageno = int(dash.callback_context.outputs_list['id']['index'].split('-')[1])

        # tabs_value == tab-10-example-graph
        tabno = int(tabs_value.split('-')[1])
        
        # If on the correct page, turn button on
        if pageno==tabno:    
            style['background-color'] = f'rgba(255,255,0,0.3)'

    return style



# Run text-to-speech on all highlighted text
@app.callback(
    Output('mp3-player', 'children'),
    [Input('tts-button', 'n_clicks'), State('tabs-example-graph', 'children'),
     State('pdf_info', 'data')]
)
def text_to_speech(n_clicks, tabs, pdf_info_s):
    if dash.callback_context.triggered[0]['value'] is None:
        return 'ok'
    
    # Get state information from the html layout
    pdf_info = json.loads(pdf_info_s)
    textboxes = {int(k):v for k,v in pdf_info['textboxes'].items()}
    annotations = pdf_info['annotations']

    # Which textboxes to include?
    texts = []
    for span_id,include in annotations.items():
        if include:
            #print(span_id)
            match = re.search('span-(\d+)-(\d+)', span_id).groups()
            pageno = int(match[0])
            ind    = int(match[1])
            #print('\t', pageno, ind)
            textbox = textboxes[pageno][ind]
            #print(textbox)
            texts.append(textbox['text'])
    text = ' '.join(texts)
    #print(text)

    #text = 'I love willie.'
    mp3_filename = text_to_mp3(text, name='demo', overwrite=True)
    return [html.Source(src=mp3_filename, type='audio/mpeg')]
    
    
    
# Make the app    
boxsize = 20
tabwidth = 130

tabs = []

# Build a 'home' tab
home_layout = html.Div(id=f'home-layout',
                       children=[
                                 html.Div('',
                                           style={'position':'absolute',
                                                  'top':'0px', 'left':f'{tabwidth}px',
                                                  'width':'612px', 'height':f'20px',
                                                  'border':'gray 1px solid'}),
                                 html.Div('',
                                          style={'position':'absolute', 'border':'gray 1px solid',
                                                 'left':f'{tabwidth}px', 'top':f'{boxsize}px',
                                                 'width':'612px', 'height':'792px'}),
                                 html.Div('',
                                          style={'position':'absolute', 
                                                 'left':f'{tabwidth+20}px', 'top':f'{boxsize+20}px',
                                                 'width':'572px', 'height':'752px',
                                                 'borderRadius':'30px 30px',
                                                 'background-color':'rgba(240,255,240)'}),
                                 dcc.Upload(id="upload-data",
                                 #html.Button(id="upload-data",
                                            children=html.Div(["Drag and drop or click to select a file to upload."]),
                                            style={'position':'absolute', 'top':'150px', 'left':f'{125+tabwidth}px',
                                                   "width": "350px", "height": "60px", "lineHeight": "60px",
                                                   "borderWidth": "1px", "borderStyle": "dashed", "borderRadius": "5px",
                                                   "textAlign": "center", "margin": "10px",
                                                   'borderRadius':'10px 10px',
                                                  },
                                            ),
                                 html.P(dcc.Markdown('No file uploaded.'),
                                        style={'position':'absolute',
                                               'top':'240px', 'left':f'{163+tabwidth}px',
                                               'width':'300px', 'height':f'50px',
                                               'text-align':'center',
                                               #'border':'gray 1px solid'
                                              },
                                        id='div-filename'
                                       ),
                                 html.Audio(id='mp3-player', controls=True, 
                                             style={'position':'absolute', 'top':'650px', 'left':f'{160+tabwidth}px',
                                                    'height':'30px', 'width':'300px'}),
                                ]
              )
home_tab = dcc.Tab(label=f'Home', value=f'tab-home', children=[home_layout])
tabs.append(home_tab)


        
# Put it all into one large webpage layout
app.layout = html.Div([
            dcc.Tabs(id="tabs-example-graph",
                     value='tab-home',
                     children=tabs,
                     persistence=True,
                     persistence_type='local',
                     vertical=True,
                     style={'position':'absolute', 'top':'0px', 'left':'0px', 'width':f'{tabwidth}px'}
                    ),
            html.Div(id='tabs-content'),
    
            # Save the textbox on/offs to allow for re-computation when paged back in
            dcc.Store(id='not-needed'),
            dcc.Store(id='pdf_info', data='', storage_type='memory'),
            html.Button('Save Annotations', id='save-ann-button',
                        style={'position':'absolute', 'top': '40px', 'left':f'{650+tabwidth}px',
                               'height':'30px', 'width':'150px',
                               'borderRadius':'10px 10px',}),
            html.Button('Unselect All on Page', id='unselect-button',
                        style={'position':'absolute', 'top':'70px', 'left':f'{650+tabwidth}px',
                               'height':'30px', 'width':'150px',
                               'borderRadius':'10px 10px',}),
            html.Button('Select All on Page', id='select-button',
                        style={'position':'absolute', 'top':'100px', 'left':f'{650+tabwidth}px',
                               'height':'30px', 'width':'150px',
                               'borderRadius':'10px 10px',}),
            html.Button('Create MP3', id='tts-button',
                        style={'position':'absolute', 'top':'130px', 'left':f'{650+tabwidth}px',
                               'height':'30px', 'width':'150px',
                               'borderRadius':'10px 10px',
                              'background-color':'rgba(128,128,255)'}),
    
            html.Div(id='dropdown-pages-holder',
                     children=[
                      # Wrap this in a container Div and then style the container
                      #    (otherwise dropdown positioning fails)
                      dcc.Dropdown(id='dropdown-pages',
                                   options=[],
                                   value=None,
                                   placeholder='',
                                   disabled=True,
                                   #persistence=True,
                                   )],
                     style={'position':'absolute', 
                            'top':'530px', 
                            'left':'0px',
                            'height':'30px', 
                            'width':f'{tabwidth}px'           
                           }),
])



if __name__ == '__main__':
    app.run_server(debug=True, port=8062)
