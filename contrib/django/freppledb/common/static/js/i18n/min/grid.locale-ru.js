(function(a){var b={isRTL:!1,defaults:{recordtext:"\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440 {0} - {1} \u0438\u0437 {2}",emptyrecords:"\u041d\u0435\u0442 \u0437\u0430\u043f\u0438\u0441\u0435\u0439 \u0434\u043b\u044f \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430",loadtext:"\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430...",pgtext:"\u0421\u0442\u0440. {0} \u0438\u0437 {1}",pgfirst:"\u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440.",pglast:"\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u0441\u0442\u0440.",
pgnext:"\u0421\u043b\u0435\u0434. \u0441\u0442\u0440.",pgprev:"\u041f\u0440\u0435\u0434. \u0441\u0442\u0440.",pgrecs:"\u0417\u0430\u043f\u0438\u0441\u0435\u0439 \u043d\u0430 \u0441\u0442\u0440.",showhide:"\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c/\u0441\u043a\u0440\u044b\u0442\u044c \u0442\u0430\u0431\u043b\u0438\u0446\u0443",savetext:"\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0435..."},search:{caption:"\u041f\u043e\u0438\u0441\u043a...",Find:"\u041d\u0430\u0439\u0442\u0438",
Reset:"\u0421\u0431\u0440\u043e\u0441",odata:[{oper:"eq",text:"\u0440\u0430\u0432\u043d\u043e"},{oper:"ne",text:"\u043d\u0435 \u0440\u0430\u0432\u043d\u043e"},{oper:"lt",text:"\u043c\u0435\u043d\u044c\u0448\u0435"},{oper:"le",text:"\u043c\u0435\u043d\u044c\u0448\u0435 \u0438\u043b\u0438 \u0440\u0430\u0432\u043d\u043e"},{oper:"gt",text:"\u0431\u043e\u043b\u044c\u0448\u0435"},{oper:"ge",text:"\u0431\u043e\u043b\u044c\u0448\u0435 \u0438\u043b\u0438 \u0440\u0430\u0432\u043d\u043e"},{oper:"bw",text:"\u043d\u0430\u0447\u0438\u043d\u0430\u0435\u0442\u0441\u044f \u0441"},
{oper:"bn",text:"\u043d\u0435 \u043d\u0430\u0447\u0438\u043d\u0430\u0435\u0442\u0441\u044f \u0441"},{oper:"in",text:"\u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432"},{oper:"ni",text:"\u043d\u0435 \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432"},{oper:"ew",text:"\u0437\u0430\u043a\u0430\u043d\u0447\u0438\u0432\u0430\u0435\u0442\u0441\u044f \u043d\u0430"},{oper:"en",text:"\u043d\u0435 \u0437\u0430\u043a\u0430\u043d\u0447\u0438\u0432\u0430\u0435\u0442\u0441\u044f \u043d\u0430"},
{oper:"cn",text:"\u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442"},{oper:"nc",text:"\u043d\u0435 \u0441\u043e\u0434\u0435\u0440\u0436\u0438\u0442"},{oper:"nu",text:"\u0440\u0430\u0432\u043d\u043e NULL"},{oper:"nn",text:"\u043d\u0435 \u0440\u0430\u0432\u043d\u043e NULL"}],groupOps:[{op:"AND",text:"\u0432\u0441\u0435"},{op:"OR",text:"\u043b\u044e\u0431\u043e\u0439"}],operandTitle:"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043e\u043f\u0435\u0440\u0430\u0446\u0438\u044e \u043f\u043e\u0438\u0441\u043a\u0430",
resetTitle:"\u0421\u0431\u0440\u043e\u0441\u0438\u0442\u044c"},edit:{addCaption:"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0437\u0430\u043f\u0438\u0441\u044c",editCaption:"\u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0437\u0430\u043f\u0438\u0441\u044c",bSubmit:"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",bCancel:"\u041e\u0442\u043c\u0435\u043d\u0430",bClose:"\u0417\u0430\u043a\u0440\u044b\u0442\u044c",saveData:"\u0414\u0430\u043d\u043d\u044b\u0435 \u0431\u044b\u043b\u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u043d\u044b! \u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f?",
bYes:"\u0414\u0430",bNo:"\u041d\u0435\u0442",bExit:"\u041e\u0442\u043c\u0435\u043d\u0430",msg:{required:"\u041f\u043e\u043b\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u043c",number:"\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u0432\u0435\u0434\u0438\u0442\u0435 \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e\u0435 \u0447\u0438\u0441\u043b\u043e",minValue:"\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u0431\u043e\u043b\u044c\u0448\u0435 \u043b\u0438\u0431\u043e \u0440\u0430\u0432\u043d\u043e",
maxValue:"\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u0434\u043e\u043b\u0436\u043d\u043e \u0431\u044b\u0442\u044c \u043c\u0435\u043d\u044c\u0448\u0435 \u043b\u0438\u0431\u043e \u0440\u0430\u0432\u043d\u043e",email:"\u043d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 e-mail",integer:"\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u0432\u0435\u0434\u0438\u0442\u0435 \u0446\u0435\u043b\u043e\u0435 \u0447\u0438\u0441\u043b\u043e",
date:"\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u0432\u0435\u0434\u0438\u0442\u0435 \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u0443\u044e \u0434\u0430\u0442\u0443",url:"\u043d\u0435\u0432\u0435\u0440\u043d\u0430\u044f \u0441\u0441\u044b\u043b\u043a\u0430. \u041d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e \u0432\u0432\u0435\u0441\u0442\u0438 \u043f\u0440\u0435\u0444\u0438\u043a\u0441 ('http://' \u0438\u043b\u0438 'https://')",nodefined:" \u043d\u0435 \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u043e!",
novalue:" \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u043c\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e!",customarray:"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u0430\u044f \u0444\u0443\u043d\u043a\u0446\u0438\u044f \u0434\u043e\u043b\u0436\u043d\u0430 \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0442\u044c \u043c\u0430\u0441\u0441\u0438\u0432!",customfcheck:"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u0430\u044f \u0444\u0443\u043d\u043a\u0446\u0438\u044f \u0434\u043e\u043b\u0436\u043d\u0430 \u043f\u0440\u0438\u0441\u0443\u0442\u0441\u0442\u0432\u043e\u0432\u0430\u0442\u044c \u0432 \u0441\u043b\u0443\u0447\u0430\u0438 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u043e\u0439 \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438!"}},
view:{caption:"\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440 \u0437\u0430\u043f\u0438\u0441\u0438",bClose:"\u0417\u0430\u043a\u0440\u044b\u0442\u044c"},del:{caption:"\u0423\u0434\u0430\u043b\u0438\u0442\u044c",msg:"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c(\u0438)?",bSubmit:"\u0423\u0434\u0430\u043b\u0438\u0442\u044c",bCancel:"\u041e\u0442\u043c\u0435\u043d\u0430"},nav:{edittext:"",edittitle:"\u0420\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c",
addtext:"",addtitle:"\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043d\u043e\u0432\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c",deltext:"",deltitle:"\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c",searchtext:"",searchtitle:"\u041d\u0430\u0439\u0442\u0438 \u0437\u0430\u043f\u0438\u0441\u0438",refreshtext:"",refreshtitle:"\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0442\u0430\u0431\u043b\u0438\u0446\u0443",
alertcap:"\u0412\u043d\u0438\u043c\u0430\u043d\u0438\u0435",alerttext:"\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0437\u0430\u043f\u0438\u0441\u044c",viewtext:"",viewtitle:"\u041f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c"},col:{caption:"\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c/\u0441\u043a\u0440\u044b\u0442\u044c \u0441\u0442\u043e\u043b\u0431\u0446\u044b",
bSubmit:"\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c",bCancel:"\u041e\u0442\u043c\u0435\u043d\u0430"},errors:{errcap:"\u041e\u0448\u0438\u0431\u043a\u0430",nourl:"URL \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d",norecords:"\u041d\u0435\u0442 \u0437\u0430\u043f\u0438\u0441\u0435\u0439 \u0434\u043b\u044f \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438",model:"\u0427\u0438\u0441\u043b\u043e \u043f\u043e\u043b\u0435\u0439 \u043d\u0435 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u0447\u0438\u0441\u043b\u0443 \u0441\u0442\u043e\u043b\u0431\u0446\u043e\u0432 \u0442\u0430\u0431\u043b\u0438\u0446\u044b!"},
formatter:{integer:{thousandsSeparator:" ",defaultValue:"0"},number:{decimalSeparator:",",thousandsSeparator:" ",decimalPlaces:2,defaultValue:"0,00"},currency:{decimalSeparator:",",thousandsSeparator:" ",decimalPlaces:2,prefix:"",suffix:"",defaultValue:"0,00"},date:{dayNames:"\u0412\u0441 \u041f\u043d \u0412\u0442 \u0421\u0440 \u0427\u0442 \u041f\u0442 \u0421\u0431 \u0412\u043e\u0441\u043a\u0440\u0435\u0441\u0435\u043d\u0438\u0435 \u041f\u043e\u043d\u0435\u0434\u0435\u043b\u044c\u043d\u0438\u043a \u0412\u0442\u043e\u0440\u043d\u0438\u043a \u0421\u0440\u0435\u0434\u0430 \u0427\u0435\u0442\u0432\u0435\u0440\u0433 \u041f\u044f\u0442\u043d\u0438\u0446\u0430 \u0421\u0443\u0431\u0431\u043e\u0442\u0430".split(" "),
monthNames:"\u042f\u043d\u0432 \u0424\u0435\u0432 \u041c\u0430\u0440 \u0410\u043f\u0440 \u041c\u0430\u0439 \u0418\u044e\u043d \u0418\u044e\u043b \u0410\u0432\u0433 \u0421\u0435\u043d \u041e\u043a\u0442 \u041d\u043e\u044f \u0414\u0435\u043a \u042f\u043d\u0432\u0430\u0440\u044c \u0424\u0435\u0432\u0440\u0430\u043b\u044c \u041c\u0430\u0440\u0442 \u0410\u043f\u0440\u0435\u043b\u044c \u041c\u0430\u0439 \u0418\u044e\u043d\u044c \u0418\u044e\u043b\u044c \u0410\u0432\u0433\u0443\u0441\u0442 \u0421\u0435\u043d\u0442\u044f\u0431\u0440\u044c \u041e\u043a\u0442\u044f\u0431\u0440\u044c \u041d\u043e\u044f\u0431\u0440\u044c \u0414\u0435\u043a\u0430\u0431\u0440\u044c".split(" "),
AmPm:["am","pm","AM","PM"],S:function(){return""},srcformat:"Y-m-d",newformat:"d.m.Y",masks:{ShortDate:"n.j.Y",LongDate:"l, F d, Y",FullDateTime:"l, F d, Y G:i:s",MonthDay:"F d",ShortTime:"G:i",LongTime:"G:i:s",YearMonth:"F, Y"}}}};a.jgrid=a.jgrid||{};a.extend(!0,a.jgrid,{defaults:{locale:"ru"},locales:{ru:a.extend({},b,{name:"\u0440\u0443\u0441\u0441\u043a\u0438\u0439",nameEnglish:"Russian"}),"ru-RU":a.extend({},b,{name:"\u0440\u0443\u0441\u0441\u043a\u0438\u0439 (\u0420\u043e\u0441\u0441\u0438\u044f)",
nameEnglish:"Russian (Russia)"})}})})(jQuery);
