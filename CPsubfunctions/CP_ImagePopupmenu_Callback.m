function CP_ImagePopupmenu_Callback(hObject,eventdata)

%% Callback used to show multiple figures.  
%% A popup menu controls the display
%% 
%% UserData is expected to be a struct with 'img' and 'title' fields,
%% one for each image entry.  
%%
%% **NOTE** Make sure that the uicontrol 'String' entries correspond to the 
%% 'UserData' entries
%%
%% See IdentifySecondary.m for an example of usage.

% $Revision$

UserData = get(hObject,'UserData'); 
h_image = findobj(gcbf,'type','image');
val = get(hObject,'Value');

set(h_image,'cdata',UserData(val).img);
title(UserData(val).title)